# -*- coding: utf-8 -*-
from odoo import fields, models  #type:ignore


class SaleOrder(models.Model):
    _inherit = "sale.order"

    mega_descripcion = fields.Char(
        string="Descripción",
        copy=True,
        index=True,
    )

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()

        order = self[:1]  # normalmente es 1
        if order.mega_descripcion:
            # Pasar la Descripción de la orden al campo Descripción general (mega_account_move_business_fields)
            if "mega_descripcion_general" in self.env["account.move"]._fields:
                vals["mega_descripcion_general"] = order.mega_descripcion

        return vals
