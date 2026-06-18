# -*- coding: utf-8 -*-

import logging
import re
from pathlib import Path

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)


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

    def unlink(self):
        if (
            not self.env.is_superuser()
            and not self.env.user.has_group('car_repair_industry.group_fleet_repair_service_manager')
            and not self.env.user.has_group('car_repair_industry.group_fleet_repair_directeur_commercial')
        ):
            raise AccessError(_(
                "No tiene permisos para eliminar evidencias externas. "
                "Solo Supervisor o Director Comercial pueden eliminar evidencias."
            ))
        self._delete_drive_files_before_unlink()
        return super().unlink()

    def _delete_drive_files_before_unlink(self):
        for evidence in self:
            file_id = evidence.drive_file_id or evidence._extract_drive_file_id()
            _logger.info(
                "Deleting external evidence %s; name=%s; file_id=%s; mime_type=%s",
                evidence.id,
                evidence.name,
                file_id or '',
                evidence.mime_type or '',
            )

            if not file_id:
                _logger.info(
                    "External evidence %s has no Drive file id; deleting only the Odoo record.",
                    evidence.id,
                )
                continue

            drive_service = evidence.repair_id._drive_get_service()
            _, _, HttpError = evidence.repair_id._drive_get_google_modules()
            try:
                drive_file = drive_service.files().get(
                    fileId=file_id,
                    fields="id,name,mimeType,driveId,trashed",
                    supportsAllDrives=True,
                ).execute()
                _logger.info(
                    "Google Drive file found for evidence %s; file_id=%s; mime_type=%s; trashed=%s.",
                    evidence.id,
                    file_id,
                    drive_file.get('mimeType'),
                    drive_file.get('trashed'),
                )

                if drive_file.get('mimeType') == 'application/vnd.google-apps.folder':
                    _logger.info(
                        "Skipping Google Drive folder deletion for evidence %s; file_id=%s.",
                        evidence.id,
                        file_id,
                    )
                    continue

                self._delete_or_trash_drive_file(drive_service, HttpError, evidence, file_id)
            except HttpError as error:
                status = self._get_http_error_status(error)
                reason = self._get_http_error_reason(error)
                if status == 404:
                    _logger.info(
                        "Google Drive file already missing before delete for evidence %s; file_id=%s; status=%s; reason=%s.",
                        evidence.id,
                        file_id,
                        status,
                        reason,
                    )
                    continue
                if status == 403:
                    _logger.warning(
                        "Google Drive get/delete forbidden for evidence %s; file_id=%s; status=%s; reason=%s; error=%s",
                        evidence.id,
                        file_id,
                        status,
                        reason,
                        error,
                    )
                    raise UserError(_(
                        "La Service Account no tiene permiso para eliminar en Google Drive. "
                        "Debe ser Administrador de la Unidad Compartida."
                    ))
                _logger.warning(
                    "Google Drive get/delete failed for evidence %s; file_id=%s; status=%s; reason=%s; error=%s",
                    evidence.id,
                    file_id,
                    status,
                    reason,
                    error,
                )
                raise UserError(_(
                    "No se pudo eliminar el archivo de Google Drive para la evidencia '%s'.\n\n"
                    "Detalle: %s"
                ) % (evidence.display_name, error))
            except Exception as error:
                _logger.warning(
                    "Unexpected Google Drive delete error for evidence %s; file_id=%s; error=%s",
                    evidence.id,
                    file_id,
                    error,
                )
                raise UserError(_(
                    "No se pudo eliminar el archivo de Google Drive para la evidencia '%s'.\n\n"
                    "Detalle: %s"
                ) % (evidence.display_name, error))

    def _delete_or_trash_drive_file(self, drive_service, HttpError, evidence, file_id):
        try:
            _logger.info(
                "Calling Google Drive delete for evidence %s; file_id=%s; action=delete.",
                evidence.id,
                file_id,
            )
            result = drive_service.files().delete(
                fileId=file_id,
                supportsAllDrives=True,
            ).execute()
            _logger.info(
                "Google Drive delete succeeded for evidence %s; file_id=%s; result=%s.",
                evidence.id,
                file_id,
                result,
            )
            return
        except HttpError as delete_error:
            delete_status = self._get_http_error_status(delete_error)
            delete_reason = self._get_http_error_reason(delete_error)
            _logger.warning(
                "Google Drive delete failed for evidence %s; file_id=%s; status=%s; reason=%s; action=delete; error=%s",
                evidence.id,
                file_id,
                delete_status,
                delete_reason,
                delete_error,
            )
            if delete_status == 403:
                raise UserError(_(
                    "La Service Account no tiene permiso para eliminar en Google Drive. "
                    "Debe ser Administrador de la Unidad Compartida."
                ))

        try:
            _logger.info(
                "Calling Google Drive trash for evidence %s; file_id=%s; action=trash.",
                evidence.id,
                file_id,
            )
            result = drive_service.files().update(
                fileId=file_id,
                body={"trashed": True},
                supportsAllDrives=True,
            ).execute()
            _logger.info(
                "Google Drive trash succeeded for evidence %s; file_id=%s; result=%s.",
                evidence.id,
                file_id,
                result,
            )
        except HttpError as trash_error:
            trash_status = self._get_http_error_status(trash_error)
            trash_reason = self._get_http_error_reason(trash_error)
            if trash_status == 404:
                _logger.warning(
                    "Google Drive file already missing on trash for evidence %s; file_id=%s; status=%s; reason=%s.",
                    evidence.id,
                    file_id,
                    trash_status,
                    trash_reason,
                )
                return
            if trash_status == 403:
                raise UserError(_(
                    "La Service Account no tiene permiso para eliminar en Google Drive. "
                    "Debe ser Administrador de la Unidad Compartida."
                ))
            _logger.warning(
                "Google Drive trash failed for evidence %s; file_id=%s; status=%s; reason=%s; action=trash; error=%s",
                evidence.id,
                file_id,
                trash_status,
                trash_reason,
                trash_error,
            )
            raise UserError(_(
                "No se pudo eliminar el archivo de Google Drive para la evidencia '%s'.\n\n"
                "Detalle: %s"
            ) % (evidence.display_name, trash_error))

    def _get_http_error_status(self, error):
        return getattr(getattr(error, 'resp', None), 'status', None)

    def _get_http_error_reason(self, error):
        return getattr(getattr(error, 'resp', None), 'reason', '')
