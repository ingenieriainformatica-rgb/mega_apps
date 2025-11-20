# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class PosConfig(models.Model):
    _inherit = "pos.config"

    l10n_co_show_cufe_receipt = fields.Boolean(
        string="Mostrar CUFE en Tirilla",
        default=True,
        help="Mostrar el CUFE y QR en la tirilla cuando la orden tiene factura electrónica aceptada"
    )

    l10n_co_auto_invoice_pos = fields.Boolean(
        string="Facturar automáticamente en POS",
        default=False,
        help="Genera la factura electrónica automáticamente al finalizar la orden y la envía a DIAN"
    )

    # def _load_pos_data_fields(self, config_id):
    #     """Extender campos cargados en el POS"""
    #     return super()._load_pos_data_fields(config_id) + ['l10n_co_show_cufe_receipt', 'l10n_co_auto_invoice_pos']
    
    # NOTA: NO es necesario implementar _load_pos_data_fields para pos.config
    # Todos los campos de pos.config se cargan automáticamente en Odoo 18
