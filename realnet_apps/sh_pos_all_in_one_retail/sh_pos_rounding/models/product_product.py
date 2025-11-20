# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models,api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_rounding_product = fields.Boolean("Is Rounding Product ?")

class Product(models.Model):
    _inherit = 'product.product'

    is_rounding_product = fields.Boolean("Is Rounding Product ?")

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['is_rounding_product']