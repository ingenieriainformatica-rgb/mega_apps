# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, fields, api

class PosConfig(models.Model):
    _inherit = "pos.config"

    sh_update_real_time_qty = fields.Boolean(
        string="Update Quantity Real Time")
    sh_invoice_ids = fields.Many2many('account.journal', string="Invoices")
    sh_update_quantity_cart_change = fields.Boolean(
        string="Update Quantity When POS Cart Change")

    def update_sh_stock(self , val):
        data = []
        notification = []
        stock_obj = self.env['stock.quant'].search([('location_id', '=', val.get('location_id')), ('product_id', '=', val.get('product_id'))])
        if stock_obj:
            data = {'product_id': val.get('product_id'), 'location_id': val.get('location_id'), 'quantity': 0, 'manual_update': val.get('manual_update'),"qaunt_id" : stock_obj.id}
            for stock in stock_obj:
                if not data.get('manual_update'):
                    stock.sh_qty += float(val.get('quantity'))
                    data["quantity"] =  stock.sh_qty
                elif data.get('manual_update', False) :
                    stock.sh_qty -= float(val.get('old_quantity'))
                    if val.get('quantity'): 
                        stock.sh_qty += float(val.get('quantity'))
                    # stock.write({'sh_qty' : data['quantity']})
                    data["quantity"] =  stock.sh_qty
                else:
                    stock.write({'sh_qty' : 0})
                    data["quantity"] =  stock.sh_qty
            notification.append(data)
        all__config =  self.search([])
        for record in all__config:
            print("\n\n\n\n\n\n\n\n notification", notification)
            record._notify('stock_update', notification)
