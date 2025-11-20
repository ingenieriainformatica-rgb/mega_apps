# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _load_pos_data_domain(self, data):
        domain = super()._load_pos_data_domain(data)
        domain = [item for item in domain if item[0] != 'state']
        print(f'\n\n domain --> {domain} ')
        return domain
        return [('state', '=', 'draft'), ('session_id', '=', data['pos.session']['data'][0]['id'])]