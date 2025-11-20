# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    # Campo computado para obtener el CUFE de la factura
    l10n_co_cufe = fields.Char(
        string="CUFE",
        compute="_compute_l10n_co_cufe",
        store=True,
        help="CUFE de la factura electrónica asociada"
    )

    # Campo para determinar si mostrar CUFE en tirilla
    l10n_co_show_cufe_on_receipt = fields.Boolean(
        string="Mostrar CUFE en tirilla",
        compute="_compute_l10n_co_show_cufe_on_receipt"
    )

    @api.depends('account_move', 'account_move.l10n_co_edi_cufe_cude_ref')
    def _compute_l10n_co_cufe(self):
        """Obtiene el CUFE de la factura asociada si existe"""
        for order in self:
            if order.account_move and order.account_move.l10n_co_edi_cufe_cude_ref:
                order.l10n_co_cufe = order.account_move.l10n_co_edi_cufe_cude_ref
            else:
                order.l10n_co_cufe = False

    @api.depends('account_move', 'account_move.l10n_co_dian_state', 'config_id.l10n_co_show_cufe_receipt')
    def _compute_l10n_co_show_cufe_on_receipt(self):
        """Determina si se debe mostrar el CUFE en la tirilla"""
        for order in self:
            order.l10n_co_show_cufe_on_receipt = (
                order.config_id.l10n_co_show_cufe_receipt
                and order.account_move
                and order.account_move.l10n_co_dian_state == 'invoice_accepted'
                and order.account_move.l10n_co_edi_cufe_cude_ref
            )

    def _generate_pos_order_invoice(self):
        """
        Override para enviar automáticamente a DIAN si está configurado
        """
        result = super()._generate_pos_order_invoice()

        # Si está habilitada la facturación automática para Colombia
        if self.config_id.l10n_co_auto_invoice_pos and self.company_id.country_id.code == 'CO':
            if self.account_move and self.account_move.l10n_co_dian_is_enabled:
                try:
                    _logger.info(f"Enviando factura {self.account_move.name} a DIAN automáticamente")
                    self.account_move.l10n_co_dian_action_send_bill_support_document()
                except Exception as e:
                    # Log error pero no bloquear el flujo
                    _logger.warning(f"Error al enviar factura a DIAN para orden {self.name}: {e}")

        return result
