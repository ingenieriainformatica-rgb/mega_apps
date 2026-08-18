# -*- coding: utf-8 -*-
from odoo import fields, models  #type:ignore


class SaleOrder(models.Model):
    _inherit = "sale.order"

    mega_descripcion = fields.Char(
        string="Descripción",
        copy=True,
        index=True,
    )
