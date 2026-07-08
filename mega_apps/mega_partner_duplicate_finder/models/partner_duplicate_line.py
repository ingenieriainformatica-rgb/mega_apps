# -*- coding: utf-8 -*-
from odoo import fields, models


class PartnerDuplicateLine(models.Model):
    _name = "partner.duplicate.line"
    _description = "Contacto encontrado dentro de un grupo de duplicados"
    _order = "id"

    group_id = fields.Many2one(
        "partner.duplicate.group",
        string="Grupo",
        required=True,
        ondelete="cascade",
        index=True,
    )
    batch_id = fields.Many2one(
        related="group_id.batch_id",
        string="Lote",
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Contacto",
        required=True,
        ondelete="cascade",
        index=True,
    )

    # Snapshots: reflejan el estado del contacto en el momento de la búsqueda,
    # se conservan aunque el contacto real cambie después (auditoría).
    name_snapshot = fields.Char(string="Nombre (snapshot)")
    vat_snapshot = fields.Char(string="Documento (snapshot)")
    email_snapshot = fields.Char(string="Email (snapshot)")
    phone_snapshot = fields.Char(string="Teléfono (snapshot)")
    mobile_snapshot = fields.Char(string="Móvil (snapshot)")
    city_snapshot = fields.Char(string="Ciudad (snapshot)")
    company_id_snapshot = fields.Many2one(
        "res.company", string="Compañía (snapshot)"
    )
    parent_id_snapshot = fields.Many2one(
        "res.partner", string="Empresa relacionada (snapshot)"
    )
    active_snapshot = fields.Boolean(string="Activo (snapshot)")

    def action_open_partner(self):
        """Abre la ficha real del contacto (solo lectura de referencia)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": self.partner_id.id,
            "view_mode": "form",
            "target": "current",
            "context": {"active_test": False},
        }
