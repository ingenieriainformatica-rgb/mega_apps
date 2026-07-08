# -*- coding: utf-8 -*-
from odoo import api, fields, models, _  #type: ignore
from odoo.exceptions import UserError  #type: ignore

REVIEWER_GROUP = "mega_partner_merge_by_vat.group_partner_merge_reviewer"
MANAGER_GROUP = "mega_partner_merge_by_vat.group_partner_merge_manager"


class PartnerMergeProposal(models.Model):
    _name = "partner.merge.proposal"
    _description = "Propuesta de fusion de contactos duplicados"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(compute="_compute_name", store=True)
    phase = fields.Selection([
        ("vat", "VAT duplicado"),
        ("name", "Nombre igual, VAT parcial"),
    ], required=True, readonly=True)
    state = fields.Selection([
        ("pending", "Pendiente"),
        ("approved", "Aprobada"),
        ("rejected", "Rechazada"),
        ("merged", "Fusionada"),
        ("error", "Error"),
    ], default="pending", required=True, tracking=True, index=True)

    vat_key = fields.Char(string="VAT del grupo", readonly=True)
    name_key = fields.Char(string="Nombre del grupo", readonly=True)

    line_ids = fields.One2many("partner.merge.proposal.line", "proposal_id", string="Contactos candidatos")

    risk_level = fields.Selection([
        ("low", "Bajo"), ("medium", "Medio"), ("high", "Alto"),
    ], compute="_compute_risk", store=True)
    risk_notes = fields.Text(string="Motivos de riesgo", compute="_compute_risk", store=True)
    has_company_partner = fields.Boolean(string="Incluye partner de compania", compute="_compute_risk", store=True)
    has_multi_company_conflict = fields.Boolean(string="Conflicto multi-compania", compute="_compute_risk", store=True)
    has_dian_validated_invoice = fields.Boolean(string="Factura DIAN validada", compute="_compute_risk", store=True)
    has_email_conflict = fields.Boolean(string="Emails distintos", compute="_compute_risk", store=True)
    user_count = fields.Integer(string="Usuarios vinculados", compute="_compute_risk", store=True)

    partner_ids_signature = fields.Char(index=True, help="Ids de los candidatos fusionables, ordenados, para deduplicar propuestas.")

    reviewer_id = fields.Many2one("res.users", string="Revisor", readonly=True)
    review_date = fields.Datetime(readonly=True)
    review_note = fields.Text(string="Nota de revision")

    merge_date = fields.Datetime(readonly=True)
    merge_error = fields.Text(readonly=True)

    active = fields.Boolean(default=True)

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends("phase", "vat_key", "name_key")
    def _compute_name(self):
        for rec in self:
            if rec.phase == "vat":
                rec.name = _("VAT %s") % (rec.vat_key or "?")
            else:
                rec.name = _("Nombre: %s") % (rec.name_key or "?")

    @api.depends(
        "phase",
        "line_ids.role",
        "line_ids.is_company_partner",
        "line_ids.has_dian_validated_invoice",
        "line_ids.snapshot_company_id",
        "line_ids.snapshot_email",
        "line_ids.snapshot_user_logins",
    )
    def _compute_risk(self):
        for rec in self:
            mergeable = rec.line_ids.filtered(lambda l: l.role != "related_child")
            reasons = []

            has_company_partner = any(mergeable.mapped("is_company_partner"))
            if has_company_partner:
                reasons.append(_(
                    "Uno de los contactos es el partner base de una compania "
                    "(res.company.partner_id): NO se puede fusionar."
                ))

            companies = {c for c in mergeable.mapped("snapshot_company_id.id") if c}
            has_multi_company_conflict = len(companies) > 1
            if has_multi_company_conflict:
                reasons.append(_("Los candidatos pertenecen a companias distintas."))

            has_dian = any(mergeable.mapped("has_dian_validated_invoice"))
            if has_dian:
                reasons.append(_("Al menos un candidato tiene facturas electronicas DIAN ya validadas."))

            emails = {(e or "").strip().lower() for e in mergeable.mapped("snapshot_email")} - {""}
            has_email_conflict = len(emails) > 1
            if has_email_conflict:
                reasons.append(_("Los candidatos tienen emails distintos."))

            logins = set()
            for logins_str in mergeable.mapped("snapshot_user_logins"):
                logins.update(l for l in (logins_str or "").split(",") if l)
            user_count = len(logins)
            if user_count > 1:
                reasons.append(_("Hay mas de un usuario vinculado entre los candidatos."))

            if rec.phase == "name":
                reasons.append(_("Coincidencia solo por nombre: requiere confirmar identidad manualmente."))
                risk_level = "high"
            elif has_company_partner or has_dian or has_multi_company_conflict:
                risk_level = "high"
            elif has_email_conflict or user_count > 1:
                risk_level = "medium"
            else:
                risk_level = "low"

            rec.has_company_partner = has_company_partner
            rec.has_multi_company_conflict = has_multi_company_conflict
            rec.has_dian_validated_invoice = has_dian
            rec.has_email_conflict = has_email_conflict
            rec.user_count = user_count
            rec.risk_level = risk_level
            rec.risk_notes = "\n".join(reasons) if reasons else _("Sin senales de riesgo detectadas.")

    # ------------------------------------------------------------------
    # Deteccion (solo lectura de res.partner, nunca fusiona)
    # ------------------------------------------------------------------

    @api.model
    def _normalize_vat(self, vat):
        return (vat or "").replace(" ", "").strip().upper()

    @api.model
    def _find_vat_groups(self):
        self.env.cr.execute("""
            SELECT array_agg(id)
            FROM res_partner
            WHERE vat IS NOT NULL
              AND vat != ''
              AND parent_id IS NULL
            GROUP BY replace(upper(vat), ' ', '')
            HAVING COUNT(*) >= 2
            ORDER BY min(id)
        """)
        groups = []
        for (ids,) in self.env.cr.fetchall():
            partners = self.env["res.partner"].with_context(active_test=False).browse(ids).exists()
            if len(partners) >= 2:
                groups.append(partners)
        return groups

    @api.model
    def _find_name_groups(self, exclude_ids=()):
        self.env.cr.execute("""
            SELECT array_agg(id)
            FROM res_partner
            WHERE parent_id IS NULL
            GROUP BY trim(lower(name))
            HAVING
              COUNT(*) >= 2
              AND COUNT(CASE WHEN vat IS NOT NULL AND vat != '' THEN 1 END) >= 1
              AND COUNT(CASE WHEN vat IS NULL OR vat = '' THEN 1 END) >= 1
              AND COUNT(
                DISTINCT CASE WHEN vat IS NOT NULL AND vat != ''
                  THEN replace(upper(vat), ' ', '') END
              ) = 1
            ORDER BY min(id)
        """)
        exclude_set = set(exclude_ids)
        groups = []
        for (ids,) in self.env.cr.fetchall():
            filtered = [i for i in ids if i not in exclude_set]
            if len(filtered) < 2:
                continue
            partners = self.env["res.partner"].with_context(active_test=False).browse(filtered).exists()
            if len(partners) >= 2:
                groups.append(partners)
        return groups

    @api.model
    def _partition_group(self, candidates):
        """ (mergeables, related_children): related_children son aquellos cuya
        cadena parent_id llega a otro miembro del propio grupo. """
        ids_set = set(candidates.ids)
        related_children = candidates.browse([])
        for partner in candidates:
            ancestor = partner.parent_id
            seen = set()
            while ancestor and ancestor.id not in seen:
                seen.add(ancestor.id)
                if ancestor.id in ids_set:
                    related_children |= partner
                    break
                ancestor = ancestor.parent_id
        return candidates - related_children, related_children

    @api.model
    def _score(self, partner):
        filled = sum(1 for f in ("city", "email", "phone") if partner[f])
        return (filled, partner.write_date)

    @api.model
    def _score_with_vat(self, partner):
        has_vat = 1 if (partner.vat and partner.vat.strip()) else 0
        filled = sum(1 for f in ("city", "email", "phone") if partner[f])
        return (has_vat, filled, partner.write_date)

    @api.model
    def _partners_with_dian_validated_invoice(self, partner_ids):
        Move = self.env["account.move"]
        if not partner_ids or "ei_is_valid" not in Move._fields:
            return set()
        moves = Move.sudo().search([
            ("partner_id", "in", list(partner_ids)),
            ("ei_is_valid", "=", True),
        ])
        return set(moves.mapped("partner_id.id"))

    def _make_line_values(self, proposal_id, partner, role, company_partner_ids, dian_ids):
        return {
            "proposal_id": proposal_id,
            "partner_id": partner.id,
            "original_partner_id": partner.id,
            "role": role,
            "snapshot_name": partner.name,
            "snapshot_vat": partner.vat,
            "snapshot_email": partner.email,
            "snapshot_phone": partner.phone,
            "snapshot_city": partner.city,
            "snapshot_company_id": partner.company_id.id,
            "snapshot_parent_id": partner.parent_id.id or 0,
            "snapshot_user_logins": ",".join(
                partner.with_context(active_test=False).user_ids.mapped("login")
            ),
            "snapshot_write_date": partner.write_date,
            "is_company_partner": partner.id in company_partner_ids,
            "has_dian_validated_invoice": partner.id in dian_ids,
            "is_archived": not partner.active,
        }

    def _create_proposal_from_group(self, candidates, phase, vat_key, name_key, company_partner_ids, excluded_vats):
        """ Crea (o no) una propuesta a partir de un grupo de candidatos.
        Devuelve una de: 'created', 'skipped_no_duplicates', 'skipped_already_processed', 'skipped_excluded_vat'.
        Nunca fusiona nada. """
        mergeables, related_children = self._partition_group(candidates)
        if len(mergeables) < 2:
            return "skipped_no_duplicates"

        signature = ",".join(str(i) for i in sorted(mergeables.ids))
        existing = self.search([
            ("partner_ids_signature", "=", signature),
            ("state", "in", ("pending", "approved", "merged", "rejected", "error")),
        ], limit=1)
        if existing:
            return "skipped_already_processed"

        vat_for_check = vat_key or next((p.vat for p in mergeables if p.vat), "")
        if self._normalize_vat(vat_for_check) in excluded_vats:
            return "skipped_excluded_vat"

        dian_ids = self._partners_with_dian_validated_invoice(mergeables.ids + related_children.ids)
        score_fn = self._score if phase == "vat" else self._score_with_vat
        ordered = mergeables.sorted(key=score_fn, reverse=True)
        dst_partner = ordered[0]

        proposal = self.create({
            "phase": phase,
            "vat_key": vat_key or "",
            "name_key": name_key or "",
            "partner_ids_signature": signature,
        })

        Line = self.env["partner.merge.proposal.line"]
        for partner in ordered:
            role = "destination" if partner.id == dst_partner.id else "candidate"
            Line.create(self._make_line_values(proposal.id, partner, role, company_partner_ids, dian_ids))
        for partner in related_children:
            Line.create(self._make_line_values(proposal.id, partner, "related_child", company_partner_ids, dian_ids))

        return "created"

    @api.model
    def run_detection(self, run_phase1=True, run_phase2=True):
        """ Punto de entrada unico de deteccion. Solo crea propuestas, jamas fusiona. """
        if not self.env.user.has_group(REVIEWER_GROUP):
            raise UserError(_("No tiene permisos para ejecutar la deteccion de duplicados."))

        summary = {
            "created": 0,
            "skipped_no_duplicates": 0,
            "skipped_already_processed": 0,
            "skipped_excluded_vat": 0,
        }

        excluded_vats = {
            self._normalize_vat(v)
            for v in self.env["partner.merge.excluded.vat"].sudo().search([]).mapped("vat")
        }
        company_partner_ids = set(self.env["res.company"].sudo().search([]).mapped("partner_id").ids)

        if run_phase1:
            for candidates in self._find_vat_groups():
                result = self._create_proposal_from_group(
                    candidates, "vat", candidates[0].vat, False,
                    company_partner_ids, excluded_vats,
                )
                summary[result] += 1

        if run_phase2:
            phase1_partner_ids = set(
                self.search([("phase", "=", "vat")]).line_ids.mapped("original_partner_id")
            )
            for candidates in self._find_name_groups(exclude_ids=phase1_partner_ids):
                result = self._create_proposal_from_group(
                    candidates, "name", False, candidates[0].name or "",
                    company_partner_ids, excluded_vats,
                )
                summary[result] += 1

        return summary

    # ------------------------------------------------------------------
    # Revalidacion (los datos pueden cambiar entre deteccion, aprobacion y ejecucion)
    # ------------------------------------------------------------------

    def _refresh_snapshots_and_risk(self):
        company_partner_ids = set(self.env["res.company"].sudo().search([]).mapped("partner_id").ids)
        for rec in self:
            partner_ids = [pid for pid in rec.line_ids.mapped("original_partner_id") if pid]
            dian_ids = self._partners_with_dian_validated_invoice(partner_ids)
            for line in rec.line_ids:
                partner = line.partner_id
                if not partner or not partner.exists():
                    continue
                line.write({
                    "snapshot_name": partner.name,
                    "snapshot_vat": partner.vat,
                    "snapshot_email": partner.email,
                    "snapshot_phone": partner.phone,
                    "snapshot_city": partner.city,
                    "snapshot_company_id": partner.company_id.id,
                    "snapshot_parent_id": partner.parent_id.id or 0,
                    "snapshot_user_logins": ",".join(
                        partner.with_context(active_test=False).user_ids.mapped("login")
                    ),
                    "snapshot_write_date": partner.write_date,
                    "is_company_partner": partner.id in company_partner_ids,
                    "has_dian_validated_invoice": partner.id in dian_ids,
                    "is_archived": not partner.active,
                })

    def _lines_still_exist(self):
        self.ensure_one()
        for line in self.line_ids:
            if not line.partner_id or not line.partner_id.exists():
                return False
        return True

    def _bulk_merge_eligibility(self):
        """ Clasifica si esta propuesta puede fusionarse desde el wizard de
        fusion masiva, SIN ejecutar nada. Reutiliza los mismos campos y la
        misma nocion de "valido" que action_approve/action_execute_merge; la
        validacion fuerte real sigue ocurriendo dentro de esos metodos al
        confirmar (no se duplica logica de aprobacion/fusion).

        Las propuestas 'pending' que pasan las validaciones duras tambien se
        consideran elegibles: el wizard las aprueba automaticamente (pidiendo
        justificacion si son de riesgo alto) antes de fusionarlas.

        Devuelve (elegible: bool, motivo: str). """
        self.ensure_one()
        if self.state not in ("pending", "approved", "error"):
            labels = {
                "rejected": _("Rechazada."),
                "merged": _("Ya fue fusionada."),
            }
            return False, labels.get(self.state, _("Estado no valido para fusion masiva."))
        if self.has_company_partner:
            return False, _("Incluye el partner base de una compania.")
        if self.has_multi_company_conflict:
            return False, _("Conflicto multi-compania.")
        destinations = self.line_ids.filtered(lambda l: l.role == "destination")
        if len(destinations) != 1:
            return False, _("No hay un unico contacto destino.")
        if not self._lines_still_exist():
            return False, _("Uno o mas contactos ya no existen desde la aprobacion.")
        return True, ""

    def action_open_bulk_merge_wizard(self):
        if not self.env.user.has_group(MANAGER_GROUP):
            raise UserError(_("No tiene permisos para ejecutar la fusion masiva de contactos."))
        if not self:
            raise UserError(_("Seleccione al menos una propuesta de fusion."))
        # El wizard y sus lineas se crean YA persistidos aqui mismo (no via
        # default_get/onchange): las lineas de un one2many resueltas solo por
        # onchange en un registro nuevo pueden perderse al guardar desde el
        # cliente web. Creando todo de una vez evita ese problema por completo.
        Wizard = self.env["partner.merge.bulk.merge.wizard"]
        wizard = Wizard.create({
            "proposal_ids": [(6, 0, self.ids)],
            "line_ids": [(0, 0, Wizard._make_line_vals(p)) for p in self],
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "partner.merge.bulk.merge.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    # ------------------------------------------------------------------
    # Aprobacion / rechazo (revision humana obligatoria)
    # ------------------------------------------------------------------

    def action_approve(self):
        if not self.env.user.has_group(REVIEWER_GROUP):
            raise UserError(_("No tiene permisos para aprobar propuestas de fusion."))
        for rec in self:
            if rec.state != "pending":
                raise UserError(_("Solo se pueden aprobar propuestas pendientes."))

            rec._refresh_snapshots_and_risk()

            if not rec._lines_still_exist():
                raise UserError(_(
                    "Uno o mas contactos de esta propuesta ya no existen. "
                    "Rechacela y vuelva a ejecutar la deteccion."
                ))
            if rec.has_company_partner:
                raise UserError(_(
                    "Esta propuesta incluye el contacto base de una compania y no puede aprobarse."
                ))
            if rec.has_multi_company_conflict:
                raise UserError(_(
                    "Los contactos de esta propuesta pertenecen a companias distintas y no pueden fusionarse."
                ))
            destinations = rec.line_ids.filtered(lambda l: l.role == "destination")
            if len(destinations) != 1:
                raise UserError(_(
                    "Debe haber exactamente un contacto marcado como Destino antes de aprobar "
                    "(cambie el campo Rol en la pestana Candidatos si la sugerencia no es correcta)."
                ))
            if rec.risk_level == "high" and not (rec.review_note or "").strip():
                raise UserError(_(
                    "Esta propuesta es de riesgo alto: debe justificar la aprobacion en la nota de revision."
                ))

            rec.write({
                "state": "approved",
                "reviewer_id": self.env.user.id,
                "review_date": fields.Datetime.now(),
            })
            rec.message_post(body=_("Propuesta aprobada por %s.") % self.env.user.name)

    def action_reject(self):
        if not self.env.user.has_group(REVIEWER_GROUP):
            raise UserError(_("No tiene permisos para rechazar propuestas de fusion."))
        for rec in self:
            if rec.state not in ("pending", "error"):
                raise UserError(_("Solo se pueden rechazar propuestas pendientes o en error."))
            if not (rec.review_note or "").strip():
                raise UserError(_("Debe indicar el motivo del rechazo en la nota de revision."))
            rec.write({
                "state": "rejected",
                "reviewer_id": self.env.user.id,
                "review_date": fields.Datetime.now(),
            })
            rec.message_post(body=_("Propuesta rechazada por %s.") % self.env.user.name)

    def action_reset_to_pending(self):
        if not self.env.user.has_group(REVIEWER_GROUP):
            raise UserError(_("No tiene permisos para reabrir propuestas de fusion."))
        for rec in self:
            if rec.state != "rejected":
                raise UserError(_("Solo se pueden reabrir propuestas rechazadas."))
            rec.write({"state": "pending"})
            rec.message_post(body=_("Propuesta reabierta por %s.") % self.env.user.name)

    # ------------------------------------------------------------------
    # Ejecucion de la fusion (reutiliza el wizard nativo de Odoo)
    # ------------------------------------------------------------------

    def action_execute_merge(self):
        if not self.env.user.has_group(MANAGER_GROUP):
            raise UserError(_("No tiene permisos para ejecutar la fusion de contactos."))

        Wizard = self.env["base.partner.merge.automatic.wizard"]
        for rec in self:
            if rec.state != "approved":
                raise UserError(_("Solo se pueden fusionar propuestas aprobadas."))

            rec._refresh_snapshots_and_risk()

            if rec.has_company_partner:
                rec._set_merge_error(_(
                    "Bloqueado: uno de los contactos es el partner base de una compania."
                ))
                continue
            if rec.has_multi_company_conflict:
                rec._set_merge_error(_(
                    "Bloqueado: los contactos pertenecen a companias distintas."
                ))
                continue
            if not rec._lines_still_exist():
                rec._set_merge_error(_(
                    "Uno o mas contactos ya no existen; los datos cambiaron desde la aprobacion."
                ))
                continue

            destinations = rec.line_ids.filtered(lambda l: l.role == "destination")
            if len(destinations) != 1 or not destinations.partner_id:
                rec._set_merge_error(_(
                    "No hay un contacto destino valido (debe haber exactamente uno marcado como Destino)."
                ))
                continue

            dst_partner = destinations.partner_id
            src_lines = rec.line_ids.filtered(lambda l: l.role == "candidate")
            src_partners = [line.partner_id for line in src_lines if line.partner_id]

            error_msg = None
            pos = 0
            while pos < len(src_partners):
                batch = src_partners[pos:pos + 2]
                batch_ids = [dst_partner.id] + [p.id for p in batch]
                try:
                    with self.env.cr.savepoint():
                        # mega_fix_module_contact.res_partner.write() bloquea cualquier
                        # escritura de 'vat' si otro partner ya existente comparte ese
                        # mismo VAT normalizado. _update_values() del core reescribe
                        # (sin cambiarlo) el vat del destino ANTES de eliminar los
                        # origenes, y en ese instante el origen (que comparte el mismo
                        # VAT, por eso estan en este grupo) todavia existe -> bloqueo
                        # falso positivo. Se limpia por SQL directo (evita re-disparar
                        # ese write() y el registro se elimina segundos despues de todas
                        # formas).
                        rec._clear_src_vat_before_merge([p.id for p in batch])
                        # No confiamos en el chequeo de email interno de _merge(): el
                        # propio core lo desactiva automaticamente si el usuario es
                        # admin/superusuario (env.is_admin()). Por eso ese chequeo se
                        # replica de forma explicita en _compute_risk/action_approve
                        # (has_email_conflict) antes de llegar aqui.
                        Wizard._merge(batch_ids, dst_partner=dst_partner, extra_checks=True)
                except Exception as exc:  # noqa: BLE001 - se registra, no se relanza
                    error_msg = str(exc)
                    break
                pos += 2

            if error_msg:
                rec._set_merge_error(error_msg)
            else:
                rec.write({
                    "state": "merged",
                    "merge_date": fields.Datetime.now(),
                    "merge_error": False,
                })
                rec.message_post(body=_("Fusion ejecutada por %s.") % self.env.user.name)

    def action_retry_merge(self):
        if not self.env.user.has_group(MANAGER_GROUP):
            raise UserError(_("No tiene permisos para ejecutar la fusion de contactos."))
        for rec in self:
            if rec.state != "error":
                raise UserError(_("Solo se pueden reintentar propuestas en error."))
            rec.write({"state": "approved", "merge_error": False})
        self.action_execute_merge()

    def _clear_src_vat_before_merge(self, src_partner_ids):
        """ Limpia el vat de los contactos origen por SQL directo (no via write())
        justo antes de fusionarlos. Ver comentario en action_execute_merge: evita
        el falso positivo de mega_fix_module_contact al reescribir el vat
        (sin cambiarlo) en el destino mientras el origen todavia existe. """
        if not src_partner_ids:
            return
        self.env.cr.execute(
            "UPDATE res_partner SET vat = NULL WHERE id IN %s",
            (tuple(src_partner_ids),),
        )
        self.env.invalidate_all()

    def _set_merge_error(self, message):
        self.write({"state": "error", "merge_error": message})
        self.message_post(body=_("Error al ejecutar la fusion: %s") % message)
