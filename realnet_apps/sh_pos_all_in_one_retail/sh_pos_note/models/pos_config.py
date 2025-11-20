# Copyright (C) Softhealer Technologies.
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    enable_orderline_note = fields.Boolean(
        "Enable Internal Note", default=False)
    display_orderline_note_receipt = fields.Boolean(
        "Display Internal Note in Receipt")
    display_order_note_payment = fields.Boolean(
        "Display General Note in Payment")
    hide_extra_note_checkbox = fields.Boolean(string = "Hide Store Extra Note")
