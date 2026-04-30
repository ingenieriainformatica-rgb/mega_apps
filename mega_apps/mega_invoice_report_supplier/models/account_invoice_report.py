# -*- coding: utf-8 -*-

from odoo import fields, models  #type: ignore
from odoo.tools import SQL  #type: ignore


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    supplier_id = fields.Many2one(
        "res.partner",
        string="Proveedor",
        readonly=True,
    )

    def _select(self):
        return SQL(
            "%s, supplier_partner.partner_id AS supplier_id",
            super()._select()
        )

    def _from(self):
        return SQL(
            """
            %s
            LEFT JOIN LATERAL (
                SELECT psi.partner_id
                FROM product_supplierinfo psi
                WHERE psi.product_tmpl_id = product.product_tmpl_id
                ORDER BY psi.sequence ASC, psi.id ASC
                LIMIT 1
            ) supplier_partner ON TRUE
            """,
            super()._from()
        )

    def _group_by(self):
        return SQL(
            "%s, supplier_partner.partner_id",
            super()._group_by()
        )
