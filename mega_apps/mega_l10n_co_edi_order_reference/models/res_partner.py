# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_send_order_reference_dian = fields.Boolean(
        string="Enviar N° Orden en XML DIAN",
        help="Si está activo y la factura tiene N° orden, el XML enviado a la DIAN "
             "incluirá el nodo cac:OrderReference con ese valor.",
    )
