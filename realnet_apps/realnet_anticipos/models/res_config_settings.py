# -*- coding: utf-8 -*-
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    anticipos_customer_account_id = fields.Many2one(
        'account.account',
        related='company_id.anticipos_customer_account_id',
        string='Cuenta de Anticipos de Clientes',
        readonly=False,
    )
    anticipos_supplier_account_id = fields.Many2one(
        'account.account',
        related='company_id.anticipos_supplier_account_id',
        string='Cuenta de Anticipos a Proveedores',
        readonly=False,
    )
