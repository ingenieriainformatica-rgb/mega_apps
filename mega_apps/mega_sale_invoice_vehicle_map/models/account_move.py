import logging
from odoo import fields, models  #type:ignore

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    vehicle = fields.Char(
        string='Vehículo',
        copy=False,
        help='Vehículo traído automáticamente desde la orden de venta.'
    )
