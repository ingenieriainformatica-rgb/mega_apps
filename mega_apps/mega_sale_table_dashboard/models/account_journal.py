import logging
from odoo import models, fields  #type: ignore

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "journal_warehouse_rel",
        "journal_id",
        "warehouse_id",
        string="Almacenes asociados",
        help="Almacenes que facturan usando este diario",
        tracking=True,
    )
    