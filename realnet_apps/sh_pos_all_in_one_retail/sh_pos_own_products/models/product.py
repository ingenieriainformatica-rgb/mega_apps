# Copyright (C) Softhealer Technologies.
# Part of Softhealer Technologies.

from odoo import models, fields , api

class PosProducts(models.Model):
    _inherit = 'product.product'

    sh_select_user = fields.Many2many(
        'res.users',string='Allocate Sales Person')

    @api.model
    def _load_pos_data_fields(self, config_id):

        result = super()._load_pos_data_fields(config_id)
        result += ['sh_select_user']
        return result


class PosProductTmplate(models.Model):
    _inherit = 'product.template'

    sh_select_user = fields.Many2many(
        'res.users',string='Allocate Sale Person')

    def create(self,vals):
        res = super(PosProductTmplate,self).create(vals)
        res.product_variant_ids.write({
            'sh_select_user' : [(6,0,res.sh_select_user.ids)]
        })

        return res

    def write(self,vals):
        res = super(PosProductTmplate,self).write(vals)
        self.product_variant_ids.write({
            'sh_select_user' : [(6,0,self.sh_select_user.ids)]
        })
        return res
    
    @api.model
    def _load_pos_data_fields(self, config_id):

        result = super()._load_pos_data_fields(config_id)
        result += ['sh_select_user']
        return result

