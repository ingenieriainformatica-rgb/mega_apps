# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PartnerDuplicateGroup(models.Model):
    _name = "partner.duplicate.group"
    _description = "Grupo de contactos repetidos"
    _order = "contact_count desc, id desc"

    batch_id = fields.Many2one(
        "partner.duplicate.batch",
        string="Lote",
        required=True,
        ondelete="cascade",
        index=True,
    )
    match_type = fields.Selection(
        [
            ("vat", "Documento"),
            ("name", "Nombre"),
        ],
        string="Tipo de coincidencia",
        required=True,
    )
    match_value = fields.Char(
        string="Valor original",
        help="Valor tal como aparece en el primer contacto encontrado del grupo.",
    )
    normalized_value = fields.Char(
        string="Valor normalizado",
        required=True,
        help="Valor usado internamente para agrupar los contactos duplicados.",
    )
    contact_count = fields.Integer(
        string="Cantidad de contactos",
        compute="_compute_contact_count",
        store=True,
    )
    line_ids = fields.One2many(
        "partner.duplicate.line", "group_id", string="Contactos"
    )
    state = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("reviewed", "Revisado"),
            ("discarded", "Descartado"),
        ],
        string="Estado",
        default="pending",
        required=True,
    )

    @api.depends("line_ids")
    def _compute_contact_count(self):
        for group in self:
            group.contact_count = len(group.line_ids)

    def action_mark_reviewed(self):
        self.write({"state": "reviewed"})

    def action_mark_discarded(self):
        self.write({"state": "discarded"})

    def action_reset_pending(self):
        self.write({"state": "pending"})
