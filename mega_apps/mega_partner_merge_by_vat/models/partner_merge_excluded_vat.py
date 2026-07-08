# -*- coding: utf-8 -*-
from odoo import fields, models #type: ignore


class PartnerMergeExcludedVat(models.Model):
    _name = "partner.merge.excluded.vat"
    _description = "VAT/NIT excluido de la deteccion de duplicados para fusion"
    _rec_name = "vat"
    _order = "vat"

    vat = fields.Char(string="VAT/NIT", required=True, index=True)
    note = fields.Char(string="Motivo", help="Ej: Consumidor final DIAN, NIT de pruebas, etc.")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("vat_uniq", "unique(vat)", "Este VAT/NIT ya esta en la lista de excluidos."),
    ]
