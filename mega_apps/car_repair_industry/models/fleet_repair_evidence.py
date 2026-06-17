# -*- coding: utf-8 -*-

import re
from pathlib import Path

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
    drive_file_id = fields.Char(string="Google Drive File ID")
    mime_type = fields.Char(string="MIME Type")
    is_image = fields.Boolean(
        string="Es imagen",
        compute='_compute_drive_preview_fields',
        store=True,
    )
    preview_url = fields.Char(
        string="Vista previa",
        compute='_compute_drive_preview_fields',
    )
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

    def _extract_drive_file_id(self):
        self.ensure_one()
        url = self.external_url or ''
        patterns = [
            r'/file/d/([^/]+)',
            r'[?&]id=([^&]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return False

    @api.depends('drive_file_id', 'external_url', 'mime_type', 'name')
    def _compute_drive_preview_fields(self):
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        for evidence in self:
            drive_file_id = evidence.drive_file_id or evidence._extract_drive_file_id()
            extension = Path(evidence.name or '').suffix.lower()
            is_image = (
                bool(evidence.mime_type and evidence.mime_type.startswith('image/'))
                or extension in image_extensions
            )
            evidence.is_image = bool(drive_file_id and is_image)
            evidence.preview_url = (
                "/car_repair/evidence/%s/image" % evidence.id
                if evidence.is_image else False
            )

    @api.constrains('external_url')
    def _check_external_url_is_google_drive(self):
        for evidence in self:
            url = (evidence.external_url or '').strip()
            if url and not url.startswith('https://drive.google.com'):
                raise ValidationError(
                    "El enlace de evidencia debe empezar por https://drive.google.com"
                )
