import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class AccountLoanLine(models.Model):
    _inherit = "account.loan"

    paid_client = fields.Boolean(
      readonly=True,
      copy=False,
      default=False
    )

    def action_open_register_payment_from_loan(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Registrar clientes pagos"),
            "res_model": "payment.clien.register.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_loan_id": self.id,
                "default_principal_amount": self.amount_borrowed,
            },
        }
