# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_co_show_cufe_receipt = fields.Boolean(
        related='pos_config_id.l10n_co_show_cufe_receipt',
        readonly=False,
        string="Mostrar CUFE en Tirilla POS"
    )

    l10n_co_auto_invoice_pos = fields.Boolean(
        related='pos_config_id.l10n_co_auto_invoice_pos',
        readonly=False,
        string="Facturación Automática POS"
    )
