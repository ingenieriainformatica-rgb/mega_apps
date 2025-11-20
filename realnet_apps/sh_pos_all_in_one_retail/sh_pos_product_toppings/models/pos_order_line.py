# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api

class PosOrderInherit(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _process_order(self, order, existing_order):
        topping_child_uuids_by_parent_uuid = self._prepare_topping_line_uuids(order)
        res = super()._process_order(order, existing_order)
        pos_order = self.browse(res)
        pos_order._link_topping_items(topping_child_uuids_by_parent_uuid)
        return res
    
    def _prepare_topping_line_uuids(self, order_vals):
        acc = {}
        for line in order_vals['lines']:
            if line[0] not in [0, 1]:
                continue

            line = line[2]

            if line.get('sh_topping_line_ids'):
                filtered_lines = list(filter(lambda l: l[0] in [0, 1] and l[2].get('id') and l[2].get('id') in line.get('sh_topping_line_ids'), order_vals['lines']))
                acc[line['uuid']] = [l[2]['uuid'] for l in filtered_lines]

            line['sh_topping_line_ids'] = False
            line['sh_base_line_id'] = False

        return acc
    
    def _link_topping_items(self, combo_child_uuids_by_parent_uuid):
        self.ensure_one()

        for parent_uuid, child_uuids in combo_child_uuids_by_parent_uuid.items():
            parent_line = self.lines.filtered(lambda line: line.uuid == parent_uuid)
            if not parent_line:
                continue
            parent_line.sh_topping_line_ids = [(6, 0, self.lines.filtered(lambda line: line.uuid in child_uuids).ids)]

class PosOrderlineInherit(models.Model):
    _inherit = 'pos.order.line'

    sh_is_has_topping = fields.Boolean(string="Has Topping")
    sh_is_topping = fields.Boolean(string="is Topping")
    sh_base_line_id =  fields.Many2one('pos.order.line', string='Base Product ')
    sh_topping_line_ids = fields.One2many('pos.order.line', 'sh_base_line_id', string='Toppings Lines')

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['sh_is_has_topping', 'sh_is_topping',"sh_base_line_id","sh_topping_line_ids"]
