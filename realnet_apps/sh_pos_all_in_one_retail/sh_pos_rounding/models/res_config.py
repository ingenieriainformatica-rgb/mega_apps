# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models
from odoo.osv.expression import OR


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def get_rounding_product(self):
        return self.env['product.product'].sudo().search([('is_rounding_product', '=', True)], limit=1).id

    sh_enable_rounding = fields.Boolean("Enable Rounding")
    round_product_id = fields.Many2one('product.product', string="Rounding Product",
                                        domain=[('is_rounding_product', '=', True)])
    rounding_type = fields.Selection([('normal', 'Normal Rounding'), (
        'fifty', 'Rounding To Fifty')], string="Rounding Type", default='normal')


    def _get_available_product_domain(self):
        res =  super()._get_available_product_domain()
        if self.limit_categories and self.iface_available_categ_ids:
            res = OR([res, [('is_rounding_product','=', True)]])
        return res