# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api  #type: ignore
from odoo.tools import SQL  #type: ignore

_logger = logging.getLogger(__name__)


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    mega_concepto = fields.Char(string="Concepto", readonly=True)

    @api.model
    def _select(self) -> SQL:
        # Extendemos el SELECT del reporte para traer el concepto desde account_move (alias move)
        return SQL(
            "%s, move.mega_concepto AS mega_concepto",
            super()._select(),
        )
