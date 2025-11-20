# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.
from odoo import models, fields, api

class Productproduct(models.Model):
    _inherit = "product.product"

    suggestion_line = fields.One2many('product.suggestion', 'product_id', string="Product Suggestion")
        # UOM feature code 
    sh_uom_line_ids = fields.One2many('sh.uom.line', 'product_id', string="UOMs")

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        fields += ['suggestion_line', 'sh_uom_line_ids']
        return fields
 # UOM feature code
class Productproduct(models.Model):
    _inherit = "pos.order.line"

    sh_uom_id = fields.Many2one('uom.uom', string='Unit Of Measurement',)  

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        result += ["sh_uom_id"]
        return result
 # UOM feature code up
class ProductSuggestion(models.Model):
    _name = "product.suggestion"
    _description = "POS Product Suggestion"

    product_id = fields.Many2one('product.product')
    product_suggestion_id = fields.Many2one(
        'product.product', required=True, string="Product Suggestion")

    @api.model
    def _load_pos_data_domain(self, data):
        return [ ]
    
    @api.model
    def _load_pos_data_fields(self, config_id):
        return [ ]
    
    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
        print('\n\n\n\n >>>>>> ',domain, fields)
        return {
            'data': self.search_read(domain, fields, load=False) if domain is not False else [],
            'fields': fields,
        }


class shUOM(models.Model):

    _name = 'sh.uom.line'
    _description = 'UOM '


    uom_id = fields.Many2one('uom.uom',string='UOM',)
    price  = fields.Float("Price")
    product_id = fields.Many2one('product.product')
    uom_name  = fields.Char(related='uom_id.name')
    sh_qty = fields.Float("Qty")
    
    @api.model
    def _load_pos_data_domain(self, data):
        return [ ]
    
    @api.model
    def _load_pos_data_fields(self, config_id):
        return [ ]
    
    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
        return {
            'data': self.search_read(domain, fields, load=False) if domain is not False else [],
            'fields': fields,
        }


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    sh_uom_id = fields.Many2one('uom.uom',string='UOM',)

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        result += ["sh_uom_id"]
        return result