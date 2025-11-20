# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PettyCashBoxLine(models.Model):
    _name = "petty.cash.box.line"
    _description = "Movimiento de Caja Menor"
    _order = "id desc"

    petty_cash_id = fields.Many2one(
        "petty.cash.box", string="Caja Menor", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(
        "res.company", string="Compañía", related="petty_cash_id.company_id", store=True, readonly=True
    )
    currency_id = fields.Many2one(
        "res.currency", string="Moneda", related="petty_cash_id.currency_id", store=True, readonly=True
    )
    partner_id = fields.Many2one(
        "res.partner", string="Contacto", help="Tercero asociado al movimiento."
    )
    move_type = fields.Selection(
        [("in", "Ingreso"), ("out", "Egreso")],
        string="Tipo",
        required=True,
        default="in",
    )
    amount = fields.Monetary(
        string="Monto",
        currency_field="currency_id",
        required=True
    )
    description = fields.Char(string="Descripción", required=True)

    @api.model_create_multi
    def create(self, vals_list):
        # 1) Validación temprana: monto > 0 por cada línea
        for vals in vals_list:
            if not vals.get("partner_id"):
                raise ValidationError(_("Debe de seleccionar el contacto!!!"))
            amount = vals.get("amount") or 0.0
            # si quieres usar la precisión de moneda, puedes obtenerla del company:
            # precision = self.env.company.currency_id.rounding
            if amount <= 0:
                raise ValidationError(_("El monto debe ser mayor a 0.00."))
        lines = super().create(vals_list)
        # Abrir automáticamente la caja si está en borrador
        for line in lines:
            box = line.petty_cash_id
            if box.state == "draft":
                # (opcional) exigir monto inicial > 0 antes de abrir
                # if not box.opening_type_quantity or box.opening_type_quantity <= 0:
                #     raise ValidationError(_("Antes de agregar movimientos, define un Monto Inicial mayor a 0."))
                box.state = "open"
        return lines
