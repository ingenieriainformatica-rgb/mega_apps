# -*- coding: utf-8 -*-
from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    anticipos_customer_account_id = fields.Many2one(
        'account.account',
        string='Cuenta de Anticipos de Clientes',
        domain="[('company_id','=',id), ('deprecated','=',False), ('reconcile','=',True), "
               " ('account_type','in',('liability_current','liability_non_current'))]",
        help='Cuenta usada para pagos de clientes sin facturas (anticipos / depósitos).'
    )
    anticipos_supplier_account_id = fields.Many2one(
        'account.account',
        string='Cuenta de Anticipos a Proveedores',
        domain="[('company_id','=',id), ('deprecated','=',False), ('reconcile','=',True), "
               " ('account_type','in',('asset_current','asset_non_current'))]",
        help='Cuenta usada para pagos a proveedores sin facturas (anticipos / anticipos a proveedores).'
    )
