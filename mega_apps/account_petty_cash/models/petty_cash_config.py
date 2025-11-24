import logging
from odoo import fields, models  #type: ignore

_logger = logging.getLogger(__name__)


class PettyCashBalance(models.Model):
    _name = "pc.cashbox.balance"
    _description = "Tipo de saldo inicial/ajuste de caja"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    TYPE_SELECTION = [
        ('control_efectivo', 'Control de efectivo'),
        ('control_efectivo_1a1', 'Control de efectivo 1a1'),
        ('control_efectivo_megasur', 'Control de efectivo MEGASUR'),
    ]

    name = fields.Selection(
      selection=TYPE_SELECTION,
      string="Tipo de saldo",
      required=True,
      tracking=True,
      copy=False,
    )
    quantity = fields.Float(
      tracking=True,
      copy=False,
      digits=(16, 2)
    )

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'El tipo de saldo debe ser único.'),
    ]
