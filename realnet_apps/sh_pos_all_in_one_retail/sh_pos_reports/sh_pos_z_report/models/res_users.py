# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api, _

class ResUsers(models.Model):
    _inherit = 'res.users'

    sh_is_allow_z_report = fields.Boolean(string="Allow to Generate Z-Report ?")

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        result.append('sh_is_allow_z_report')
        return result
