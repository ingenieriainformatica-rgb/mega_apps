# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api

class PosConfig(models.Model):
    _inherit = "pos.config"

    allow_sh_pos_cancel = fields.Boolean('res.groups', compute='_get_group_sh_pos_cancel',)


    def _get_group_sh_pos_cancel(self):
        for rec in self:
            if self.env.ref('sh_pos_all_in_one_retail.group_sh_pos_cancel').users in self.env.user: 
                rec.allow_sh_pos_cancel = True
            else:
                rec.allow_sh_pos_cancel = False


class ResCompany(models.Model):
    _inherit = "res.company"


    @api.model
    def _load_pos_data_fields(self, config_id):
        result =super()._load_pos_data_fields(config_id)
        result +=  [
            'pos_operation_type'
        ]
        return result
