# -*- coding: utf-8 -*-
from odoo import fields, models  # type: ignore


class AccountMove(models.Model):
    _inherit = 'account.move'

    customer_order_ref = fields.Char(
        string='N° orden',
        copy=False,
        help='Número de orden del cliente. Se muestra en el PDF de factura cuando tiene valor.',
    )
