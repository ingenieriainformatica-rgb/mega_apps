# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models  # type: ignore

_logger = logging.getLogger(__name__)


class PettyCashBoxBalance(models.Model):
    _inherit = "petty.cash.box"

    resulting_balance = fields.Monetary(
        string="Saldo resultante",
        compute="_compute_resulting_balance",
        store=True,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec.resulting_balance = rec.opening_type_quantity or 0.0
        return records

    # ======================
    # Defaults del formulario
    # ======================
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        resulting_balance = res.get("opening_type_quantity", 0.0)
        res["resulting_balance"] = resulting_balance
        return res

    @api.depends(
        "opening_type_quantity",
        "line_ids.move_type",
        "line_ids.amount",
        "state",
    )
    def _compute_resulting_balance(self):
        for rec in self:
            if rec.state in ("open", "draft"):
                balance = rec.opening_type_quantity or 0.0

                for line in rec.line_ids:
                    if line.move_type == "in":
                        balance += line.amount or 0.0
                    elif line.move_type == "out":
                        balance -= line.amount or 0.0

                rec.resulting_balance = balance
