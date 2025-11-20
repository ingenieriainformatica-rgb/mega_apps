# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, fields,api


class ResUsers(models.Model):
    _inherit = "res.users"

    pos_config_id = fields.Many2one("pos.config", string="POS Config")
    sh_is_direct_logout = fields.Boolean(string="Is Direct LogOut ?")

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        result.extend(['pos_config_id', 'sh_is_direct_logout'])
        return result