import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class AccountLoanLine(models.Model):
    _inherit = "account.loan.line"

    # Campos de estado (por ahora solo visuales; los usaremos luego)
    paid_fee = fields.Boolean(
      string="Pagado",
      readonly=True,
      copy=False,
      default=False
    )
    payment_move_id = fields.Many2one(
      "account.move",
      string="Asiento de pago",
      readonly=True,
      copy=False
    )
    loan_state = fields.Selection(
        related="loan_id.state",
        store=False,
        string="Estado del préstamo",
        readonly=True,
    )
    loan_paid_client = fields.Boolean(
        related="loan_id.paid_client",
        store=False,
        readonly=True,
    )

    def action_open_register_payment(self):
        """Abrir popup para esta cuota (sin contabilizar aún)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Registrar proveedores pagos"),
            "res_model": "loan.register.payment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_line_id": self.id,
                "default_loan_id": self.loan_id.id,
                "default_principal_amount": self.principal,
            },
        }
