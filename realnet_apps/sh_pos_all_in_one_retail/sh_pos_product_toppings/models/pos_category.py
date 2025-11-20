# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api

class PosCategoryInherit(models.Model):
    _inherit = "pos.category"

    sh_product_topping_ids = fields.Many2many('product.product', string="Toppings", domain="[('available_in_pos', '=', True)]")

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['sh_product_topping_ids']
