# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _  #type: ignore
from odoo.exceptions import ValidationError  #type: ignore

_logger = logging.getLogger(__name__)

STATE_SALE = "sale"


class SaleOrder(models.Model):
    _inherit = "sale.order"

    advisor_id = fields.Many2one(
        comodel_name="res.partner",
        string="Asesor",
        domain="[('is_advisor', '=', True)]",
        help="Contacto marcado como asesor (en Contactos).",
        index=True,
        required=True
    )

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()

        order = self[:1]  # normalmente es 1
        if order.advisor_id:
            # ✅ Pasar el nombre del asesor al campo Concepto (mega_account_move_business_fields)
            if "mega_concepto" in self.env["account.move"]._fields:
                vals["mega_concepto"] = order.advisor_id.name

        return vals

    def write(self, vals):
        # Si están intentando cambiar el estado a sale, exigir asesor
        if vals.get("state") == STATE_SALE:
            no_advisor = self.filtered(lambda o: not o.advisor_id and not vals.get("advisor_id"))
            if no_advisor:
                raise ValidationError(
                    _("No puedes pasar a Orden de Venta sin Asesor. Asigna un asesor antes de continuar.")
                )

        res = super().write(vals)