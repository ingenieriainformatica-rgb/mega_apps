# Part of Softhealer Technologies.

from odoo import models, fields, api
from datetime import datetime, timedelta
from collections import defaultdict


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    sh_return_qty = fields.Float(string="Return Qty.")
    sh_exchange_qty = fields.Float(string="Exchange Qty.")

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        result += ["sh_return_qty","sh_exchange_qty"]
        return result


class PosOrder(models.Model):
    _inherit = 'pos.order'

    is_return_order = fields.Boolean(string="Is Return Order?", readonly=True)
    is_exchange_order = fields.Boolean(
        string="Is Exchange Order?", readonly=True)
    old_pos_reference = fields.Char(string="Return Order", readonly=True)
    return_status = fields.Selection([
        ('nothing_return', 'Nothing Returned'),
        ('partialy_return', 'Partialy Returned'),
        ('fully_return', 'Fully Returned')
    ], string="Return Status ", default='nothing_return',
        readonly=True, copy=False, help="Return status of Order")
    total_return_order = fields.Integer(compute='_compute_return_order_total_', string="Total Return Order ",)
    total_exchange_order = fields.Integer(compute='_compute_exchange_order_total_', string="Total Exchange Order ",)

    @api.depends('pos_reference')
    def _compute_return_order_total_(self):
        pos_refs = [rec.pos_reference for rec in self if rec.pos_reference]
        if not pos_refs:
            return
        domain = [('old_pos_reference', 'in', pos_refs), ('is_return_order', '=', True)]
        grouped_data = self.env['pos.order'].read_group(
            domain,
            fields=['old_pos_reference'],
            groupby=['old_pos_reference']
        )
        return_map = {}
        for data in grouped_data:
            key = data.get('old_pos_reference')
            count = len(self.env['pos.order'].search(data['__domain']))
            return_map[key] = count

        for rec in self:
            rec.total_return_order = return_map.get(rec.pos_reference, 0)


    @api.depends('pos_reference')
    def _compute_exchange_order_total_(self):
        pos_refs = [rec.pos_reference for rec in self if rec.pos_reference]
        if not pos_refs:
            return
        domain = [('old_pos_reference', 'in', pos_refs), ('is_exchange_order', '=', True)]
        grouped_data = self.env['pos.order'].read_group(
            domain,
            fields=['old_pos_reference'],
            groupby=['old_pos_reference']
        )
        exchange_map = {}
        for data in grouped_data:
            key = data.get('old_pos_reference')
            count = len(self.env['pos.order'].search(data['__domain']))
            exchange_map[key] = count

        for rec in self:
            rec.total_exchange_order = exchange_map.get(rec.pos_reference, 0)


    def action_view_return(self):
        return {
            'name': 'Return Order',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'list,form',
            'domain': [('old_pos_reference', '=', self.pos_reference), ('is_return_order', '=', True)],
            'res_model': 'pos.order',
            'target': 'current',
        }

    def action_view_exchange(self):
        return {
            'name': 'Exchange Order',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'list,form',
            'domain': [('old_pos_reference', '=', self.pos_reference), ('is_exchange_order', '=', True)],
            'res_model': 'pos.order',
            'target': 'current',
        }
