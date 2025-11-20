import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount
from markupsafe import Markup, escape

_logger = logging.getLogger(__name__)


class PaymentClienRegisterWizard(models.TransientModel):
    _name = "payment.clien.register.wizard"
    _description = "Registrar pago cliente"

    loan_id = fields.Many2one("account.loan", string="Préstamo", readonly=True)
    date = fields.Date(string="Fecha de pago", default=fields.Date.context_today, required=True)

    # Monto (solo lectura desde la cuota)
    currency_id = fields.Many2one(related="loan_id.currency_id", store=False, readonly=True)
    principal_amount = fields.Monetary(string="Principal", currency_field="currency_id", readonly=True)
    interest_amount = fields.Monetary(string="Interés", currency_field="currency_id", readonly=True)
    total_amount = fields.Monetary(string="Total a pagar", currency_field="currency_id", readonly=True)

    # Parámetros del pago
    journal_id = fields.Many2one(
        "account.journal",
        string="Diario bancario",
        required=True,
    )
    # Lista computada de métodos disponibles para ese diario (igual que en account.payment)
    available_payment_method_line_ids = fields.Many2many(
        'account.payment.method.line',
        compute='_compute_available_payment_method_lines',
        string="Métodos disponibles",
        store=False,
    )

    payment_method_line_id = fields.Many2one(
        "account.payment.method.line",
        string="Método de pago",
        required=True,
        domain="[('id','in', available_payment_method_line_ids)]",
    )
    partner_id = fields.Many2one(
      "res.partner",
      string="Cliente",
      required=True,
      help="Tercero del préstamo (opcional)."
    )
    memo = fields.Char(string="Concepto", default=lambda s: _("Recibir dinero préstamo"))
    payment_type = fields.Selection(
        [('outbound', 'Enviar'), ('inbound', 'Recibir')],
        string="Tipo de pago",
        default='inbound',
        required=True,
    )

    @api.depends('journal_id', 'payment_type')
    def _compute_available_payment_method_lines(self):
        """Trae exactamente lo que ves en la pestaña 'Pagos salientes' del diario."""
        for w in self:
            if w.journal_id:
                lines = w.journal_id._get_available_payment_method_lines(w.payment_type or 'inbound')
                w.available_payment_method_line_ids = [(6, 0, lines.ids)]
            else:
                w.available_payment_method_line_ids = [(5, 0, 0)]

    @api.onchange('journal_id', 'payment_type')
    def _onchange_journal_id(self):
        """Filtra el combo y propone el primer método válido del diario."""
        if not self.journal_id:
            self.payment_method_line_id = False
            return {'domain': {'payment_method_line_id': [('id', '=', False)]}}

        # Igual que usa Odoo en account.payment
        lines = self.journal_id._get_available_payment_method_lines(self.payment_type or 'inbound')

        # Autoselección si el actual no es válido
        if lines:
            if not self.payment_method_line_id or self.payment_method_line_id not in lines:
                self.payment_method_line_id = lines[:1]
        else:
            self.payment_method_line_id = False

        # Devolver dominio explícito (refuerza el de la vista)
        return {'domain': {'payment_method_line_id': [('id', 'in', lines.ids)]}}




    def action_confirm_accoun_loan(self):
        self.ensure_one()
        w = self

        # Validaciones
        if not w.journal_id:
            raise UserError(_("Debes seleccionar un diario bancario."))
        if not w.payment_method_line_id:
            raise UserError(_("Debes seleccionar un método de pago."))
        if not w.principal_amount or w.principal_amount <= 0:
            raise UserError(_("El importe debe ser mayor que 0."))

        # Valores del pago (borrador)
        vals = {
            "payment_type": w.payment_type,          # en tu flujo: 'inbound'
            "partner_type": "customer",
            "journal_id": w.journal_id.id,
            "payment_method_line_id": w.payment_method_line_id.id,
            "partner_id": w.partner_id.id or False,
            "amount": w.principal_amount,            # usa w.total_amount si quieres capital + interés
            "date": fields.Date.context_today(w),
            "memo": w.memo or _("Pago cuota préstamo %s") % (w.loan_id.display_name,),
        }

        # 1) Crear el pago
        payment = self.env["account.payment"].create(vals)

        # 1.1) Forzar la cuenta destino del asiento (cuenta de CORTO PLAZO del préstamo)
        # Intentamos con los posibles nombres que hayas usado en el modelo del préstamo
        short_acc = (
            getattr(w.loan_id, 'short_term_account_id', False)
            or getattr(w.loan_id, 'loan_short_term_account_id', False)
            or getattr(w.loan_id, 'loan_short_account_id', False)
        )

        _logger.info(f"\n\n {short_acc} \n\n")

        if short_acc:
            payment.destination_account_id = short_acc.id

        payment.action_post()

        # 2) Actualizar el préstamo
        w.loan_id.write({"paid_client": True})

        # 3) Post al chatter (con link al pago)
        amount_text = format_amount(self.env, w.principal_amount, w.loan_id.currency_id)
        # link = f'<a href="#" data-oe-model="account.payment" data-oe-id="{payment.id}">{payment.display_name}</a>'
        link = Markup('<a href="#" data-oe-model="account.payment" data-oe-id="%s">%s</a>') % (
            payment.id,
            escape(payment.display_name or _("Borrador de pago")),
         )

        # Enlace clickeable al pago
        link = Markup(
            '<a href="#" data-oe-model="account.payment" data-oe-id="%s" '
            'style="font-weight:600; text-decoration:none; color:#1a73e8;">%s</a>'
        ) % (
            payment.id,
            escape(payment.display_name or _("Borrador de pago")),
        )

        # Texto del monto formateado
        amount_text = format_amount(self.env, w.principal_amount, w.loan_id.currency_id)

        # Cuerpo del mensaje con ícono y estructura bonita
        body = Markup(
            '<i class="fa fa-money text-success" title="Pago de cliente"></i> '
            + _("Se creó el pago de cliente %s por %s (Diario: %s · Método: %s).")
        ) % (
            link,
            escape(amount_text),
            escape(w.journal_id.display_name or ""),
            escape(w.payment_method_line_id.name or ""),
        )

        # Publicar el mensaje en el chatter del préstamo
        w.loan_id.message_post(
            body=body,
            subtype_xmlid="mail.mt_note",
        )

        payment.message_post(
            body=Markup(
                '<i class="fa fa-briefcase text-primary" title="Préstamo"></i> '
                + _("Creado desde el préstamo %s por %s.")
            ) % (
                Markup(
                    '<a href="#" data-oe-model="account.loan" data-oe-id="%s" '
                    'style="font-weight:600; text-decoration:none; color:#1a73e8;">%s</a>'
                ) % (
                    w.loan_id.id,
                    escape(w.loan_id.display_name or _("Préstamo")),
                ),
                escape(self.env.user.display_name or ""),
            ),
            subtype_xmlid="mail.mt_note",
        )


        # (Opcional) suscribir al cliente como seguidor del préstamo
        if w.partner_id:
            w.loan_id.message_subscribe(partner_ids=[w.partner_id.id])

        # Abrir el borrador
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "view_mode": "form",
            "res_id": payment.id,
            "target": "current",
        }
