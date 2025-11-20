import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from markupsafe import Markup, escape
from odoo.tools.misc import format_amount

_logger = logging.getLogger(__name__)


class LoanRegisterPaymentWizard(models.TransientModel):
    _name = "loan.register.payment.wizard"
    _description = "Registrar pago de cuota de préstamo"

    loan_id = fields.Many2one("account.loan", string="Préstamo", required=True, readonly=True)
    line_id = fields.Many2one(
        "account.loan.line",
        string="Cuota",
        required=True,
        domain="[('loan_id','=',loan_id)]",
        readonly=True,
    )
    date = fields.Date(string="Fecha de pago", default=fields.Date.context_today, required=True)

    # Monto (solo lectura desde la cuota)
    currency_id = fields.Many2one(related="loan_id.currency_id", store=False, readonly=True)
    principal_amount = fields.Monetary(string="Principal", currency_field="currency_id", readonly=True)
    interest_amount  = fields.Monetary(string="Interés", currency_field="currency_id", readonly=True)
    total_amount     = fields.Monetary(string="Total a pagar", currency_field="currency_id", readonly=True)

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
      string="Proveedor (Banco)",
      required=True,
      help="Tercero del préstamo (opcional)."
    )
    memo = fields.Char(string="Concepto", default=lambda s: _("Pago cuota préstamo"))
    payment_type = fields.Selection(
        [('outbound', 'Enviar'), ('inbound', 'Recibir')],
        string="Tipo de pago",
        default='outbound',
        required=True,
    )

    @api.depends('journal_id', 'payment_type')
    def _compute_available_payment_method_lines(self):
        for w in self:
            if w.journal_id:
                lines = w.journal_id._get_available_payment_method_lines(w.payment_type or 'outbound')
                w.available_payment_method_line_ids = [(6, 0, lines.ids)]
            else:
                w.available_payment_method_line_ids = [(5, 0, 0)]

    @api.onchange('journal_id', 'payment_type')
    def _onchange_journal_id(self):
        if not self.journal_id:
            self.payment_method_line_id = False
            return {'domain': {'payment_method_line_id': [('id', '=', False)]}}

        lines = self.journal_id._get_available_payment_method_lines(self.payment_type or 'outbound')

        # autoselección del primero válido
        if lines:
            if not self.payment_method_line_id or self.payment_method_line_id not in lines:
                self.payment_method_line_id = lines[:1].id  # puedes asignar id o recordset
        else:
            self.payment_method_line_id = False

        return {'domain': {'payment_method_line_id': [('id', 'in', lines.ids)]}}

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        line = self.env['account.loan.line'].browse(vals.get('line_id'))
        if line:
            # Los nombres de campos estándar son estos en account_loan
            principal = getattr(line, "principal", 0.0)
            interest = getattr(line, "interest", 0.0)
            total = getattr(line, "payment_amount", principal + interest)
            vals.update({
                "principal_amount": principal,
                "interest_amount": interest,
                "total_amount": total,
                "date": line.date or fields.Date.context_today(self),
            })
        return vals

    def action_continue(self):
      self.ensure_one()
      w = self

      # Validaciones mínimas
      if not w.journal_id:
          raise UserError(_("Debes seleccionar un diario bancario."))
      if not w.payment_method_line_id:
          raise UserError(_("Debes seleccionar un método de pago."))
      if not w.total_amount or w.total_amount <= 0:
          raise UserError(_("El importe debe ser mayor que 0."))

      # Armar valores del pago (en borrador)
      vals = {
          "payment_type": w.payment_type,          # outbound/inbound según tu variable
          "journal_id": w.journal_id.id,
          "partner_type": "supplier",
          "payment_method_line_id": w.payment_method_line_id.id,
          "partner_id": w.partner_id.id or False,
          "amount": w.total_amount,
          "date": fields.Date.context_today(w),
          # Mantengo tu 'memo' y además lleno 'ref' (campo real en account.payment)
          "memo": w.memo or _("Pago cuota préstamo %s") % (w.loan_id.display_name,),
      }

      # Multi-moneda (si aplica)
      if w.loan_id.currency_id and w.loan_id.currency_id != w.loan_id.company_id.currency_id:
          vals["currency_id"] = w.loan_id.currency_id.id

      # Crear borrador
      payment = self.env["account.payment"].create(vals)
      short_acc = (
          getattr(w.loan_id, 'short_term_account_id', False)
          or getattr(w.loan_id, 'loan_short_term_account_id', False)
          or getattr(w.loan_id, 'loan_short_account_id', False)
      )

      _logger.info(f"\n\n {short_acc} \n\n")

      if short_acc:
          payment.destination_account_id = short_acc.id

      payment.action_post()

      # (Opcional) enlazar el borrador a la línea si tienes ese campo
      if getattr(w.line_id, "x_payment_draft_id", False) is not False:
          w.line_id.x_payment_draft_id = payment.id

      # Marcar cuota como pagada (flag) SOLO si el create salió bien
      if w.line_id:
          w.line_id.write({"paid_fee": True})

      # --------- Chatter bonito (en préstamo y en pago) ---------
      try:
          # Link al pago
          payment_link = Markup(
              '<a href="#" data-oe-model="account.payment" data-oe-id="%s" '
              'style="font-weight:600; text-decoration:none; color:#1a73e8;">%s</a>'
          ) % (payment.id, escape(payment.display_name or _("Borrador de pago")))

          # Link al préstamo
          loan_link = Markup(
              '<a href="#" data-oe-model="account.loan" data-oe-id="%s" '
              'style="font-weight:600; text-decoration:none; color:#1a73e8;">%s</a>'
          ) % (w.loan_id.id, escape(w.loan_id.display_name or _("Préstamo")))

          # Monto formateado
          amount_text = format_amount(self.env, w.total_amount, w.loan_id.currency_id)

          # En el PRÉSTAMO
          body_loan = Markup(
              '<i class="fa fa-money text-success" title="Pago de proveedor"></i> '
              + _("Se creó el pago de <strong>proveedor</strong> %s por %s (Diario: %s · Método: %s) fecha: %s.")
          ) % (
              payment_link,
              escape(amount_text),
              escape(w.journal_id.display_name or ""),
              escape(w.payment_method_line_id.name or ""),
              escape(w.date or ""),
          )
          w.loan_id.message_post(body=body_loan, subtype_xmlid="mail.mt_note")

          # En el PAGO
          body_pay = Markup(
              '<i class="fa fa-briefcase text-primary" title="Préstamo"></i> '
              + _("Creado desde el préstamo %s por %s.")
          ) % (
              loan_link,
              escape(self.env.user.display_name or ""),
          )
          payment.message_post(body=body_pay, subtype_xmlid="mail.mt_note")

      except Exception:
          # No romper el flujo si por alguna razón falla el HTML del chatter
          pass
      # ----------------------------------------------------------

      # Abrir el borrador creado
      return {
          "type": "ir.actions.act_window",
          "res_model": "account.payment",
          "view_mode": "form",
          "res_id": payment.id,
          "target": "current",
      }
