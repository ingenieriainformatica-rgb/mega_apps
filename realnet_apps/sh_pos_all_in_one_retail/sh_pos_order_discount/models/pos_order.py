# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models, api


class ShPosOrder(models.Model):
    _inherit = "pos.order"

    sh_global_discount = fields.Float(string="Global Discount")

    @api.model
    def _order_fields(self, ui_order):
        res = super()._order_fields(ui_order)
        res["sh_global_discount"] = ui_order.get("sh_global_discount", False)
        return res

    def _export_for_ui(self, order):
        res = super()._export_for_ui(order)
        res["sh_global_discount"] = order.sh_global_discount
        return res