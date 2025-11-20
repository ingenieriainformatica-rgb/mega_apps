# Copyright (C) Softhealer Technologies.
# Part of Softhealer Technologies.

from odoo import models, fields,api

class posCustomerInherit(models.Model):
    _inherit = 'res.partner'

    sh_enable_max_dic = fields.Boolean(string='Set maximum customer discount')
    sh_maximum_discount = fields.Float(string='Discount ')
    sh_discount_type = fields.Selection([('percentage', 'Percentage(%)'), (
        'fixed', 'Fixed')], string='Discount Type', default='percentage')
    
    @api.model
    def _load_pos_data_fields(self, config_id):
        result =super()._load_pos_data_fields(config_id)
        result +=  [
            'sh_enable_max_dic',
            'sh_maximum_discount',
            'sh_discount_type',
        ]
        return result

   
