# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FleetRepairEvidence(models.Model):
    _name = 'fleet.repair.evidence'
    _description = "External Fleet Repair Evidence"
    _order = 'uploaded_at desc, id desc'

    repair_id = fields.Many2one(
        'fleet.repair',
        string="Repair Order",
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(string="Nombre", required=True)
    evidence_type = fields.Selection(
        [
            ('recepcion', 'Recepción'),
            ('diagnostico', 'Diagnóstico'),
            ('reparacion', 'Reparación'),
            ('entrega', 'Entrega'),
            ('otro', 'Otro'),
        ],
        string="Tipo",
        required=True,
        default='recepcion',
    )
    external_url = fields.Char(string="Enlace de Drive", required=True)
    description = fields.Text(string="Descripción")
    uploaded_by = fields.Many2one(
        'res.users',
        string="Usuario",
        default=lambda self: self.env.user,
        readonly=True,
    )
    uploaded_at = fields.Datetime(
        string="Fecha",
        default=fields.Datetime.now,
        readonly=True,
    )
    active = fields.Boolean(default=True)

    @api.constrains('external_url')
    def _check_external_url_is_google_drive(self):
        for evidence in self:
            url = (evidence.external_url or '').strip()
            if url and not url.startswith('https://drive.google.com'):
                raise ValidationError(
                    "El enlace de evidencia debe empezar por https://drive.google.com"
                )
