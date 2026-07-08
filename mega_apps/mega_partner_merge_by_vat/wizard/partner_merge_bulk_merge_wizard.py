# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..models.partner_merge_proposal import MANAGER_GROUP


class PartnerMergeBulkMergeWizard(models.TransientModel):
    _name = "partner.merge.bulk.merge.wizard"
    _description = "Fusion masiva de propuestas de fusion de contactos"

    proposal_ids = fields.Many2many("partner.merge.proposal", string="Propuestas seleccionadas")
    line_ids = fields.One2many("partner.merge.bulk.merge.wizard.line", "wizard_id", string="Detalle")
    state = fields.Selection([
        ("confirm", "Confirmar"),
        ("done", "Resultado"),
    ], default="confirm", required=True)
    result_message = fields.Text(readonly=True)
    justification = fields.Text(
        string="Justificacion",
        help="Se usa como nota de revision al aprobar automaticamente las propuestas "
             "pendientes de riesgo alto incluidas en este lote. Obligatoria si hay alguna.",
    )

    count_total = fields.Integer(string="Total seleccionadas", compute="_compute_counts")
    count_eligible = fields.Integer(string="Se fusionaran", compute="_compute_counts")
    count_blocked = fields.Integer(string="Bloqueadas", compute="_compute_counts")
    count_high_risk = fields.Integer(string="De riesgo alto", compute="_compute_counts")
    count_pending_to_approve = fields.Integer(
        string="Pendientes que se aprobaran", compute="_compute_counts",
    )
    count_pending_high_risk = fields.Integer(
        string="Pendientes de riesgo alto", compute="_compute_counts",
    )

    # No hay default_get para poblar line_ids: el wizard y sus lineas se crean
    # ya persistidos desde partner.merge.proposal.action_open_bulk_merge_wizard()
    # (ver comentario ahi). Esto evita depender de onchange/web_save del
    # cliente web para un one2many de un registro nuevo.

    @api.model
    def _make_line_vals(self, proposal):
        eligible, reason = proposal._bulk_merge_eligibility()
        destinations = proposal.line_ids.filtered(lambda l: l.role == "destination")
        sources = proposal.line_ids.filtered(lambda l: l.role == "candidate")
        return {
            "proposal_id": proposal.id,
            "eligible": eligible,
            "block_reason": reason,
            "dst_name": destinations[:1].snapshot_name or "",
            "src_names": ", ".join(sources.mapped("snapshot_name")),
        }

    @api.depends("line_ids.eligible", "line_ids.proposal_id.risk_level", "line_ids.proposal_id.state")
    def _compute_counts(self):
        for wiz in self:
            wiz.count_total = len(wiz.line_ids)
            wiz.count_eligible = len(wiz.line_ids.filtered("eligible"))
            wiz.count_blocked = wiz.count_total - wiz.count_eligible
            wiz.count_high_risk = len(wiz.line_ids.filtered(
                lambda l: l.eligible and l.proposal_id.risk_level == "high"
            ))
            pending_eligible = wiz.line_ids.filtered(
                lambda l: l.eligible and l.proposal_state == "pending"
            )
            wiz.count_pending_to_approve = len(pending_eligible)
            wiz.count_pending_high_risk = len(pending_eligible.filtered(
                lambda l: l.proposal_id.risk_level == "high"
            ))

    def action_confirm(self):
        self.ensure_one()
        if not self.env.user.has_group(MANAGER_GROUP):
            raise UserError(_("No tiene permisos para ejecutar la fusion masiva de contactos."))

        eligible_lines = self.line_ids.filtered("eligible")
        if not eligible_lines:
            raise UserError(_("No hay ninguna propuesta elegible para fusionar en este lote."))

        proposals = eligible_lines.mapped("proposal_id")
        pending = proposals.filtered(lambda p: p.state == "pending")
        high_risk_pending = pending.filtered(lambda p: p.risk_level == "high")
        if high_risk_pending and not (self.justification or "").strip():
            raise UserError(_(
                "Hay %s propuesta(s) pendientes de riesgo alto en este lote: escriba una "
                "justificacion antes de aprobarlas y fusionarlas."
            ) % len(high_risk_pending))

        approve_errors = []
        if pending:
            note = (self.justification or "").strip() or _(
                "Aprobada automaticamente en fusion masiva por %s."
            ) % self.env.user.name
            pending.write({"review_note": note})
            # Se aprueba una por una (mismo metodo action_approve ya existente,
            # sin duplicar su logica) para que si una falla la revalidacion no
            # se detenga todo el lote.
            for p in pending:
                try:
                    with self.env.cr.savepoint():
                        p.action_approve()
                except Exception as exc:  # noqa: BLE001 - se registra, no se relanza
                    approve_errors.append((p, str(exc)))

        proposals.invalidate_recordset()
        approved = proposals.filtered(lambda p: p.state == "approved")
        error_state = proposals.filtered(lambda p: p.state == "error")

        # Reutiliza integramente los metodos ya existentes (ambos soportan
        # multi-record): no se duplica ninguna logica de validacion/fusion.
        if approved:
            approved.action_execute_merge()
        if error_state:
            error_state.action_retry_merge()

        proposals.invalidate_recordset()
        ok = proposals.filtered(lambda p: p.state == "merged")
        failed = proposals - ok

        lines = [
            _("Propuestas fusionadas correctamente: %s") % len(ok),
            _("Propuestas con error: %s") % len(failed),
        ]
        for p in failed:
            lines.append(" - %s: %s" % (p.name, p.merge_error or _("error desconocido")))
        if approve_errors:
            lines.append(_("Propuestas que no se pudieron aprobar:"))
            for p, err in approve_errors:
                lines.append(" - %s: %s" % (p.name, err))

        self.write({
            "result_message": "\n".join(lines),
            "state": "done",
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }


class PartnerMergeBulkMergeWizardLine(models.TransientModel):
    _name = "partner.merge.bulk.merge.wizard.line"
    _description = "Linea de resumen para la fusion masiva de propuestas"
    _order = "eligible desc, id"

    wizard_id = fields.Many2one(
        "partner.merge.bulk.merge.wizard", required=True, ondelete="cascade",
    )
    proposal_id = fields.Many2one("partner.merge.proposal", required=True, readonly=True)
    phase = fields.Selection(related="proposal_id.phase")
    risk_level = fields.Selection(related="proposal_id.risk_level")
    proposal_state = fields.Selection(related="proposal_id.state", string="Estado")
    dst_name = fields.Char(string="Destino", readonly=True)
    src_names = fields.Char(string="Origenes", readonly=True)
    eligible = fields.Boolean(string="Se fusionara", readonly=True)
    block_reason = fields.Char(string="Motivo de bloqueo", readonly=True)
