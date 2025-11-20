# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api


class ShCashInOut(models.Model):
    _name = 'sh.cash.in.out'
    _description = "Cash In Out"

    sh_transaction_type = fields.Selection(
        [('cash_in', 'Cash In'), ('cash_out', 'Cash Out')], string="Transaction Type", required=True)
    sh_amount = fields.Float(string="Amount")
    sh_reason = fields.Char(string="Reason")
    sh_session = fields.Many2one('pos.session', string="Session")
    sh_date = fields.Datetime(
        string='Date', readonly=True,  )
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.model
    def try_cash_in_out(self, session, _type, amount, reason , sh_date):
        
        if _type == 'in':
           data = self.env['sh.cash.in.out'].create(
                {'sh_amount': amount, 'sh_reason': reason, 'sh_session': session, 'sh_transaction_type': 'cash_in', "sh_date" : sh_date})
        else:
           data = self.env['sh.cash.in.out'].create(
                {'sh_amount': amount, 'sh_reason': reason, 'sh_session': session, 'sh_transaction_type': 'cash_out' , "sh_date" : sh_date})
        if data.id:
            all_config = self.env["pos.config"].search([])
            for config in all_config:
                config._notify(('CASH_IN_OUT_CREATE', {'data': data.id}))

    @api.model
    def _load_pos_data_domain(self, data):
        return [('sh_session', '=',  data['pos.config']['data'][0]['current_session_id'])]
    
    @api.model
    def _load_pos_data_fields(self, config_id):
        return []
    
    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
        return {
            'data': self.search_read(domain, fields, load=False) if domain is not False else [],
            'fields': fields,
        }