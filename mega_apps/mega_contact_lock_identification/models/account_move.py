# -*- coding: utf-8 -*-
from odoo import models, _

# Facturas/notas credito de cliente y proveedor: aplica la validacion.
# Se excluye deliberadamente 'entry' (asientos contables generales, que
# pueden no tener un tercero fiscal) y los recibos ('out_receipt'/'in_receipt').
IDENTIFICATION_REQUIRED_MOVE_TYPES = ("out_invoice", "out_refund", "in_invoice", "in_refund")


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        to_check = self.filtered(lambda m: m.move_type in IDENTIFICATION_REQUIRED_MOVE_TYPES)
        for move in to_check:
            move.partner_id.commercial_partner_id._check_mega_commercial_identification(
                _("contabilizar %s", move.name if move.name and move.name != "/" else move.display_name)
            )
        return super()._post(soft=soft)
