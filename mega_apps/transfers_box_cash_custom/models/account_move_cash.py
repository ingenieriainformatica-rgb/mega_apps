# -*- coding: utf-8 -*-
import logging
from datetime import date, timedelta
from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

CTX_KEY = 'page_origin'
CTX_VAL = 'transfers_box'
FLAG = 'is_cash_transfer'  # boolean en account.journal

class AccountMoveCash(models.Model):
    _inherit = "account.move"

    # ---- Dominio centralizado para diarios de transferencias ----
    def _cash_transfer_domain(self, company):
        return [
            (FLAG, '=', True),
            ('type', '=', 'general'),
            '|', ('company_id', '=', company.id), ('company_id', '=', False),
        ]

    # Recalcula diarios adecuados y limpia journal_id si no cuadra
    def _compute_suitable_journal_ids(self):
        super()._compute_suitable_journal_ids()
        if self.env.context.get(CTX_KEY) == CTX_VAL:
            for move in self:
                dom = self._cash_transfer_domain(move.company_id)
                journals = self.env['account.journal'].search(dom)
                move.suitable_journal_ids = journals
                if move.journal_id and move.journal_id not in journals:
                    move.journal_id = False  # evita que “quede” un diario no válido

    # Default de diario: en tu pantalla especial no aceptes el del super si no cumple
    @api.model
    def _get_default_journal(self):
        if self.env.context.get(CTX_KEY) == CTX_VAL:
            dom = self._cash_transfer_domain(self.env.company)
            return self.env['account.journal'].search(dom, limit=1)
        return super()._get_default_journal()

    @api.model
    def _get_default_journal_id(self):
        j = self._get_default_journal()
        return j.id if j else False
