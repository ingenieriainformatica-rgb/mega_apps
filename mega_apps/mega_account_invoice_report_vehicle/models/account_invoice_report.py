# -*- coding: utf-8 -*-
from odoo import fields, models, api  # type: ignore
from odoo.tools import SQL  #type: ignore


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    vehicle = fields.Char(
        string='Vehículo',
        readonly=True,
    )

    @api.model
    def _select(self) -> SQL:
        # Extendemos el SELECT del reporte para traer el concepto desde account_move (alias move)
        return SQL(
            "%s, move.vehicle AS vehicle",
            super()._select(),
        )