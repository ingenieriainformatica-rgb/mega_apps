# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

OPEN_STATES = ("draft", "open")


class PettyCashBox(models.Model):
    _name = "petty.cash.box"
    _description = "Caja Menor"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"
    _rec_name = "sequence"

    # ======================
    # Campos
    # ======================
    user_id = fields.Many2one(
        "res.users", string="Responsable",
        default=lambda s: s.env.user, required=True, tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", string="Compañía",
        required=True, default=lambda s: s.env.company, index=True, tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency", string="Moneda",
        related="company_id.currency_id", readonly=True, store=True,
    )
    date_open = fields.Datetime(
        string="Fecha de Apertura",
        default=lambda s: fields.Datetime.now(), required=True, tracking=True,
    )
    date_closed = fields.Datetime(string="Fecha de cierre")
    amount_start = fields.Monetary(
        string="Monto Inicial", currency_field="currency_id", tracking=True,
        help="Saldo inicial de la caja para esta apertura.",
    )
    amount_available = fields.Monetary(
        string="Monto Disponible", currency_field="currency_id",
        store=True, readonly=True,
        help="Saldo final al cierre (igual al inicial por ahora; se ajusta con movimientos).",
    )
    state = fields.Selection(
        [("draft", "Borrador"), ("open", "Abierta"), ("closed", "Cerrada")],
        string="Estado", default="draft", required=True, tracking=True, index=True,
    )
    line_ids = fields.One2many("petty.cash.box.line", "petty_cash_id", string="Movimientos")
    sequence = fields.Char(
        string="Referencia", readonly=True, copy=False,
        default="Borrador", index=True, tracking=True,
    )
    opening_type_id = fields.Many2one(
        "pc.cashbox.balance", string="Tipo de apertura",
        tracking=True, help="Clasifica y propone el saldo inicial.",
    )
    opening_type_quantity = fields.Float(
        string="Valor del tipo (referencia)", compute="_compute_opening_type_quantity",
        digits=(16, 2), store=False, readonly=True, copy=False,
        help="Valor de referencia tomado del Tipo de Apertura seleccionado.",
    )

    # ======================
    # Computes
    # ======================
    @api.depends("opening_type_id", "opening_type_id.quantity")
    def _compute_opening_type_quantity(self):
        for rec in self:
            rec.opening_type_quantity = rec.opening_type_id.quantity or 0.0

    # ======================
    # Helpers internos
    # ======================
    def _ctx_source(self):
        """Bandera de origen que viene de la acción: 'control_efectivo' | 'control_efectivo_1a1' | 'megatecnicentro' | '1a1' ..."""
        src = (self.env.context or {}).get("option_control") or ""
        return (src or "").strip().lower()

    def _resolve_opening_type(self, vals_source=None):
        """Devuelve pc.cashbox.balance según contexto/alias, o None."""
        Balance = self.env["pc.cashbox.balance"]
        source = (vals_source or self._ctx_source())
        if source:
            # Busca por nombre insensible a mayúsculas (ajusta a 'code' si tu modelo lo usa)
            return Balance.search([("name", "ilike", source)], limit=1)
        return False

    def _next_sequence_for_source(self, company, source):
        """Retorna el siguiente número de secuencia según la ‘fuente’."""
        seq_model = self.env["ir.sequence"]
        source = (source or "").lower()

        # Selección por XMLID (simple y explícita)
        if source in ("control_efectivo_1a1", "1a1"):
            xmlid = "account_petty_cash.seq_petty_cash_box_1a1"
        else:
            # default: Mega
            xmlid = "account_petty_cash.seq_petty_cash_box"

        try:
            seq_rec = self.env.ref(xmlid)
            return seq_rec.with_company(company).next_by_id()
        except ValueError:
            # Fallback por código compartido
            return seq_model.with_company(company).next_by_code("petty.cash.box") or "/"

    # ======================
    # Creación
    # ======================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # --- Company context ---
            company = self.env.company
            if vals.get("company_id"):
                company = self.env["res.company"].browse(vals["company_id"])

            source = (self.env.context or {}).get("option_control")
            src_norm = (source or "").strip().lower()
            _logger.info("petty.cash.box.create source=%s company=%s", src_norm, company.id)

            # --- Validación: solo 1 caja abierta por compañía y tipo ---
            # Nota: Opening type se resuelve contra 'source'.
            opening = None
            if not vals.get("opening_type_id"):
                opening = self._resolve_opening_type(src_norm)
                if not opening:
                    raise ValidationError(_("No hay 'Tipo de apertura' configurado para: %s") % (source or _("(sin origen)")))
                vals["opening_type_id"] = opening.id
            else:
                opening = self.env["pc.cashbox.balance"].browse(vals["opening_type_id"])

            already_open = self.search_count([
                ("company_id", "=", company.id),
                ("state", "in", OPEN_STATES),
                ("opening_type_id", "=", opening.id),
            ])
            if already_open:
                raise ValidationError(_("Ya existe una caja abierta para este tipo de apertura en la compañía. Ciérrala antes de crear otra."))

            # --- Monto inicial (snapshot) ---
            if "amount_start" in vals:
                if vals["amount_start"] is None:
                    raise ValidationError(_("Debe definir un Saldo inicial (puede ser 0 o negativo)."))
            else:
                if opening.quantity is None:
                    raise ValidationError(_("El 'Tipo de apertura' no tiene un valor inicial definido (puede ser 0 o negativo)."))
                vals["amount_start"] = opening.quantity

            # --- Secuencia ---
            if not vals.get("sequence") or vals["sequence"] in ("New", "Borrador", "/"):
                vals["sequence"] = self._next_sequence_for_source(company, src_norm)

        return super().create(vals_list)

    # ======================
    # Acciones
    # ======================
    def action_closed_box_cash(self):
        """Cierra la caja: saldo final = inicial + ingresos - egresos; actualiza tipo y notifica."""
        for rec in self:
            if rec.state != "open":
                raise ValidationError(_("Solo puedes cerrar una caja en estado Abierta."))

            currency = rec.currency_id or rec.company_id.currency_id
            start = rec.opening_type_quantity or 0.0
            ingresos = sum(l.amount for l in rec.line_ids if l.move_type == "in")
            egresos = sum(l.amount for l in rec.line_ids if l.move_type == "out")
            final = currency.round(start + ingresos - egresos)

            rec.write({
                "amount_start": start,              # snapshot del valor de tipo usado
                "amount_available": final,          # saldo final
                "state": "closed",
                "date_closed": fields.Datetime.now(),
            })

            if rec.opening_type_id:
                rec.opening_type_id.write({"quantity": final})

            # Notificación por correo / chatter
            # try:
            #     template = self.env.ref("account_petty_cash.mail_template_petty_cash_closed", raise_if_not_found=False)
            #     email_to = (rec.user_id.partner_id.email or rec.company_id.email or "").strip()
            #     email_from = (rec.company_id.email or self.env.user.email or "no-reply@localhost").strip()

            #     if template and email_to:
            #         template.with_context(
            #             lang=rec.user_id.lang or self.env.lang,
            #             email_layout_xmlid="mail.mail_notification_light",
            #         ).send_mail(
            #             rec.id, force_send=True,
            #             email_values={"email_to": email_to, "email_from": email_from},
            #         )
            #     else:
            #         if not email_to:
            #             _logger.warning("Caja %s: sin email de destinatario.", rec.sequence)
            #         rec.message_post(
            #             body=_("Caja cerrada. Inicial: %(ini)s | Ingresos: %(inn)s | Egresos: %(out)s | Final: %(fin)s") % {
            #                 "ini": start, "inn": ingresos, "out": egresos, "fin": final,
            #             },
            #             subtype_xmlid="mail.mt_comment",
            #         )
            # except Exception as e:
            #     _logger.exception("No se pudo enviar el correo de cierre de caja %s: %s", rec.sequence, e)

             # ------- Notificación por correo (template) -------
        try:
            template = self.env.ref('account_petty_cash.mail_template_petty_cash_closed', raise_if_not_found=False)
            # 1) Responsable + compañía (fallback)
            primary_to = (rec.user_id.partner_id.email or rec.company_id.email or "").strip()

            # 2) Grupo de notificación
            notify_group = self.env.ref('account_petty_cash.group_petty_cash_notify', raise_if_not_found=False)
            group_partners = notify_group and notify_group.users.mapped('partner_id') or self.env['res.partner']
            # Filtrar con email válido
            group_partners = group_partners.filtered(lambda p: p.email)

            # 3) Evitar duplicados y construir destinos
            emails = set()
            if primary_to:
                emails.add(primary_to)
            emails.update(p.email.strip() for p in group_partners)

            email_to = ", ".join(sorted(emails))

            # 4) Remitente
            email_from = (rec.company_id.email or self.env.user.email or "no-reply@localhost").strip()

            if template and email_to:
                # Puedes usar recipient_ids si prefieres que cada partner reciba como destinatario (y respete preferencias)
                email_values = {
                    "email_to": email_to,                       # todos visibles en Para:
                    # "recipient_ids": [(6, 0, group_partners.ids)],  # alternativa: destinatarios como partners
                    "email_from": email_from,
                }
                template.with_context(
                    lang=rec.user_id.lang or self.env.lang,
                    email_layout_xmlid="mail.mail_notification_light",
                ).send_mail(rec.id, force_send=True, email_values=email_values)
            else:
                # Sin plantilla o sin destinatarios -> chatter
                if not email_to:
                    _logger.warning("Caja %s: sin destinatarios para notificación.", rec.sequence)
                rec.message_post(
                    body=_("Caja cerrada. Inicial: %(ini)s | Ingresos: %(inn)s | Egresos: %(out)s | Final: %(fin)s") % {
                        "ini": start, "inn": ingresos, "out": egresos, "fin": final,
                    },
                    subtype_xmlid="mail.mt_comment",
                )
        except Exception as e:
            _logger.exception("No se pudo enviar el correo de cierre de caja %s: %s", rec.sequence, e)

    # ======================
    # Restricciones de borrado
    # ======================
    def unlink(self):
        refs = ", ".join(self.mapped("sequence") or self.mapped("display_name"))
        raise UserError(_("No está permitido eliminar registros de caja menor.\nRegistros: %s") % refs)

    # ======================
    # Defaults del formulario
    # ======================
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        source = self._ctx_source()
        opening = self._resolve_opening_type(source)

        if "opening_type_id" in fields_list and opening:
            res.setdefault("opening_type_id", opening.id)

        if "opening_type_quantity" in fields_list:
            res["opening_type_quantity"] = opening.quantity if opening else 0.0

        if "amount_start" in fields_list and not res.get("amount_start"):
            res["amount_start"] = opening.quantity if opening else 0.0

        _logger.info("petty.cash.box.default_get source=%s opening=%s", source, opening and opening.name)
        return res
