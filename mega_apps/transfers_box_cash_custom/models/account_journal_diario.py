from odoo import models, fields  # type: ignore[import]

class AccountJournal(models.Model):
    _inherit = "account.journal"

    is_cash_transfer = fields.Boolean(
        string="¿Usar en transferencias de caja?",
        help="Si está marcado, este diario se mostrará para transferencias de caja.",
        default=False,
        tracking=True
    )
