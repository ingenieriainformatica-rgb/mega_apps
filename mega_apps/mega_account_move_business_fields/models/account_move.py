# -*- coding: utf-8 -*-
from odoo import fields, models  #type:ignore


class AccountMove(models.Model):
    _inherit = "account.move"

    mega_concepto = fields.Char(
        string="Concepto",
        copy=True,
        index=True,
    )
    mega_descripcion_general = fields.Char(
        string="Descripción general",
        copy=True,
        index=True,
    )
