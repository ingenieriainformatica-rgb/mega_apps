# -*- coding: utf-8 -*-
from odoo import fields, models  # type: ignore


class MegaDianTokenFile(models.Model):
    _name = "mega.dian.token.file"
    _description = "Registro Token DIAN"
    _order = "id desc"

    token_id = fields.Many2one(
        "mega.dian.token",
        string="Token DIAN",
        required=True,
        ondelete="cascade",
    )

    tipo_documento = fields.Char(
        string="Tipo de documento",
        required=True,
    )

    folio = fields.Char(
        string="Folio",
    )

    prefijo = fields.Char(
        string="Prefijo",
    )

    fecha_emision_dian = fields.Date(
        string="Fecha emisión DIAN",
    )

    nit_emisor = fields.Char(
        string="NIT emisor",
    )

    nombre_emisor = fields.Char(
        string="Nombre emisor",
    )

    iva = fields.Float(
        string="IVA",
        digits=(16, 2),
    )

    total = fields.Float(
        string="Total",
        digits=(16, 2),
    )

    cufe = fields.Char(
        string="CUFE",
    )


    ######## Estos nuevos campos son para el proceso de validación token Dian ########

    partner_id = fields.Many2one(
        "res.partner",
        string="Proveedor encontrado",
        readonly=True
    )
    move_id = fields.Many2one(
        "account.move",
        string="Factura Odoo",
        readonly=True
    )
    fecha_factura_odoo = fields.Date(
        string="Fecha factura Odoo",
        readonly=True,
    )

    odoo_ref = fields.Char(string="Referencia Odoo", readonly=True)
    odoo_total = fields.Float(string="Total Odoo", digits=(16, 2), readonly=True)

    odoo_iva = fields.Float(
        string="IVA Odoo",
        digits=(16, 2),
        readonly=True,
    )

    validation_status = fields.Selection([
        ("pending", "Pendiente"),
        ("matched", "Conciliado"),
        ("partial", "Coincidencia parcial"),
        ("not_found", "No encontrado"),
        ("multiple", "Múltiples coincidencias"),
    ], string="Estado validación", default="pending", readonly=True)

    validation_note = fields.Text(string="Observación validación", readonly=True)

    is_reconciled = fields.Boolean(string="Conciliado", tracking=True)

    impuestos_info = fields.Text(
        string="Impuestos DIAN",
        readonly=True,
    )

