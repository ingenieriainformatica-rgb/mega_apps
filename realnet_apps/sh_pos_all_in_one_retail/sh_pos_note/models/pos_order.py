# Copyright (C) Softhealer Technologies.
from odoo import fields, models, api


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    line_note = fields.Char("Line Note ")

class PosOrder(models.Model):
    _inherit = "pos.order"

    order_note = fields.Char("Order Note ")

