# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models,api

class PosSessionInherit(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        data += ['stock.quant', 'stock.location' ,"stock.warehouse"]
        return data
