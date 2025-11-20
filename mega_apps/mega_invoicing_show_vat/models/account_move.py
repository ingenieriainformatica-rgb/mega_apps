# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

GROUP_ID_VAT = 14     # <-- tu ID de grupo IVA
VAT_ID = 1            # <-- tu ID del code DIAN '01'
TAX_NAME = 'tax'


class AccountMove(models.Model):
    _inherit = 'account.move'

    amount_vat_only = fields.Monetary(
        string='IVA',
        currency_field='company_currency_id',
        compute='_compute_amount_vat_only',
        store=True,
        help='Suma de líneas de impuesto cuyo grupo es de tipo VAT (IVA).',
        group_operator='sum',
    )

    # ---------- Helpers ----------
    def _get_iva_total(self):
        """Retorna el total de IVA (balance en moneda de la compañía) para cada move."""
        self.ensure_one()
        tax_lines = self.line_ids.filtered(
            lambda l: l.display_type == TAX_NAME
            and l.tax_group_id and l.tax_group_id.id == GROUP_ID_VAT
            and l.tax_line_id and l.tax_line_id.l10n_co_edi_type
            and getattr(l.tax_line_id.l10n_co_edi_type, 'id', None) == VAT_ID
        )
        return sum(tax_lines.mapped('balance'))

    def _signed_iva_total(self):
        """Devuelve el total de IVA con signo según el tipo de documento."""
        self.ensure_one()
        if self.move_type not in ('in_invoice', 'out_invoice', 'out_refund', 'in_refund'):
            return 0.0
        total = self._get_iva_total() or 0.0
        # in_invoice => negativo, out_invoice => positivo
        return -abs(total) if self.move_type in ('in_invoice', 'out_refund') else abs(total)

    # ---------- Compute ----------
    @api.depends(
        'line_ids.balance',
        'line_ids.display_type',                       # <- añade display_type al depends
        'line_ids.tax_line_id',
        'line_ids.tax_line_id.tax_group_id',
        'move_type',
        'company_currency_id',
    )
    def _compute_amount_vat_only(self):
        for move in self:
            move.amount_vat_only = move._signed_iva_total()
            _logger.info(
                "\n\nIVA botón | %s (%s) = %s \n",
                move.display_name or move.id, move.move_type, move.amount_vat_only
            )

    # ---------- Botón / Acción manual (opcional) ----------
    def calculated_iva(self):
      """Calcula y asigna el total de IVA según tipo de documento."""
      for move in self:
          move.amount_vat_only = move._signed_iva_total()
          _logger.info(
              "\n\nIVA botón | %s (%s) = %s \n",
              move.display_name or move.id, move.move_type, move.amount_vat_only
          )
