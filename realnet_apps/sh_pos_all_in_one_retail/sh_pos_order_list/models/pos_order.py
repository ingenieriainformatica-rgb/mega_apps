# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api, _
from datetime import datetime, timedelta


class PosOrder(models.Model):
    _inherit = 'pos.order'

    assigned_config = fields.Many2many(
        "pos.config", string=" Sh Assigned Config")
    sequence_number = fields.Integer(
        string='Sequence Number ', help='A session-unique sequence number for the order', default=1)

    @api.model
    def _load_pos_data_domain(self, data):
        domain = super()._load_pos_data_domain(data)
        domain = [tup for tup in domain if tup[0]
                  != 'state' and tup[0] != 'session_id']
        sh_load_order_by = data['pos.config']['data'][0]['sh_load_order_by']
        if sh_load_order_by == "session_wise":
            if data['pos.config']['data'][0]['sh_session_wise_option'] == "current_session":
                domain = [('session_id', '=', data['pos.session']['data'][0]['id'])]
            elif data['pos.config']['data'][0]['sh_session_wise_option'] == "last_no_session":
                session_ids = self.env['pos.session'].search(
                    [], limit=data['pos.config']['data'][0]['sh_last_no_session']).ids
                domain = [('session_id', 'in', session_ids)]
        elif sh_load_order_by == "day_wise":
            if data['pos.config']['data'][0]['sh_day_wise_option'] == "current_day":
                start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1) - timedelta(microseconds=1)
                domain = [('date_order', '>=', start_date), ('date_order', '<=', end_date)]
            elif data['pos.config']['data'][0]['sh_session_wise_option'] == "last_no_session":
                start_date = (datetime.now() - timedelta(days=data['pos.config']['data'][0]['sh_last_no_days'])).replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
                domain = [('date_order', '>=', start_date), ('date_order', '<=', end_date)]
        return domain


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    sh_line_id = fields.Char(string='Number')
