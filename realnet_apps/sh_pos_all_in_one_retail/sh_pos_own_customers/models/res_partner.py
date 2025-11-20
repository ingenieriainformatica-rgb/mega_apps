# Copyright (C) Softhealer Technologies.
# Part of Softhealer Technologies.

from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.partner'

    sh_own_customer = fields.Many2many(
        'res.users', 'pos_own_partner_list', string='Allocate Sale Person')

    @api.model
    def _load_pos_data_fields(self, config_id):
        result =super()._load_pos_data_fields(config_id)
        result +=  [
            'sh_own_customer'
        ]
        return result
