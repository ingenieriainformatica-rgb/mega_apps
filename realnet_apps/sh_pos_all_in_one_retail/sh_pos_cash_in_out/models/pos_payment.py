# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api
from odoo.osv.expression import OR


class PosPAyment(models.Model):
    _inherit = 'pos.payment'

    @api.model
    def _load_pos_data_domain(self, data):
        domain = super()._load_pos_data_domain(data)
        domain = OR([domain, [('session_id', '=',  data['pos.config']['data'][0]['current_session_id'])]])
        return domain
        return [('pos_order_id', 'in', [order['id'] for order in data['pos.order']['data']])]