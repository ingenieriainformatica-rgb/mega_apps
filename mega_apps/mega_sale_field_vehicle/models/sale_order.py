from odoo import models, fields, api, _  #type: ignore
from odoo.exceptions import ValidationError  #type: ignore


class SaleOrder(models.Model):
    _inherit = "sale.order"

    vehicle = fields.Char(
        string="Vehículo",
        required=True,
        help="Placa: ABC123"
    )
