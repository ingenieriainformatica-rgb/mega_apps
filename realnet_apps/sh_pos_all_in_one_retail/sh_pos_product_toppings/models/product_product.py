# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api

class PosProductInherit(models.Model):
    _inherit = "product.product"

    sh_is_global_topping = fields.Boolean(string="Global Topping")
    sh_topping_ids = fields.Many2many('product.product', 'product_pos_toppings', 'name', string="Toppings", domain="[('available_in_pos', '=', True)]")
    sh_topping_group_ids = fields.Many2many('sh.topping.group', 'product_topping_group', string="Topping Group")

    @api.onchange('sh_topping_group_ids')
    def _onchange_sh_topping_group_ids(self):
        topping_groups = self.env['sh.topping.group'].browse(self.sh_topping_group_ids.ids)
        topping_ids = []
        if topping_groups:
            for topping_groupid in topping_groups:
                for tid in topping_groupid.toppinds_ids:
                    topping_ids.append(tid.id)
        self.update({'sh_topping_ids':[(6,0,topping_ids)] })

    def action_update_toppings(self):
        return {
            'name': 'Update Toppings',
            'res_model': 'sh.mass.update.topings',
            'view_mode': 'form',
            'context': {
                'active_model': 'product.product',
                'active_ids': self.ids,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['sh_is_global_topping',"sh_topping_ids" ,"sh_topping_group_ids","type","qty_available","virtual_available"]
