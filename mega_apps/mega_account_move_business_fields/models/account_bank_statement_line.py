# -*- coding: utf-8 -*-
from odoo import fields, models  #type:ignore


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    mega_concepto = fields.Char(
        related="move_id.mega_concepto",
        string="Concepto",
        readonly=True,
    )
