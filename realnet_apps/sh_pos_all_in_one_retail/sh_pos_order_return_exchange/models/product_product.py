# Part of Softhealer Technologies.

from odoo import models, fields, api
from datetime import datetime, timedelta


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        fields += [ "sh_product_non_returnable", "sh_product_non_exchangeable"]
        return fields