# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, api

class PosOrderType(models.Model):
    _inherit = "sh.order.type"


    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', 'in', data['pos.config']['data'][0]['order_types_ids'])]
    
    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['name', 'img', 'is_home_delivery']
    
    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
        return {
            'data': self.search_read(domain, fields, load=False) if domain is not False else [],
            'fields': fields,
        }