# -*- coding: utf-8 -*-

import base64
import binascii
import io
import logging
import mimetypes
from pathlib import Path

from odoo import fields, models, _
from odoo.exceptions import UserError


ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_IMAGE_MIMETYPES = {'image/jpeg', 'image/png', 'image/webp'}

_logger = logging.getLogger(__name__)


class FleetRepairDriveUploadWizard(models.TransientModel):
    _name = 'fleet.repair.drive.upload.wizard'
    _description = "Upload Fleet Repair Photos to Drive"

    repair_id = fields.Many2one(
        'fleet.repair',
        string="Recepción",
        required=True,
        readonly=True,
    )
    repair_sequence = fields.Char(
        string="Recepción",
        related='repair_id.sequence',
        readonly=True,
    )
    evidence_type = fields.Selection(
        [
            ('recepcion', 'Recepción'),
            ('diagnostico', 'Diagnóstico'),
            ('reparacion', 'Reparación'),
            ('entrega', 'Entrega'),
            ('otro', 'Otro'),
        ],
        string="Tipo de evidencia",
        required=True,
        default='recepcion',
    )
    description = fields.Text(string="Descripción")
    line_ids = fields.One2many(
        'fleet.repair.drive.upload.wizard.line',
        'wizard_id',
        string="Fotos",
    )

    def action_upload_to_drive(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Debe seleccionar al menos una imagen."))

        validated_files = self._validate_upload_batch()

        for file_data in validated_files:
            file_data.setdefault('evidence_category', 'otro')

        evidences = self.repair_id._drive_upload_evidence_images(
            validated_files,
            evidence_type=self.evidence_type,
            description=self.description,
        )

        self.line_ids.unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Google Drive"),
                'message': _("%s foto(s) subida(s) correctamente a Drive.") % len(evidences),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def _validate_upload_batch(self):
        validated_files = []
        for line in self.line_ids:
            validated_files.append(line._prepare_validated_image_file())
        return validated_files

    def _rollback_uploaded_drive_files(self, drive_service, uploaded_files):
        for drive_file in uploaded_files:
            file_id = drive_file.get('id')
            if not file_id:
                continue
            try:
                drive_service.files().delete(
                    fileId=file_id,
                    supportsAllDrives=True,
                ).execute()
                _logger.info("Rolled back uploaded Google Drive file %s.", file_id)
            except Exception as delete_error:
                _logger.warning(
                    "Could not delete uploaded Google Drive file %s during rollback: %s",
                    file_id,
                    delete_error,
                )
                try:
                    drive_service.files().update(
                        fileId=file_id,
                        body={'trashed': True},
                        supportsAllDrives=True,
                    ).execute()
                    _logger.info("Moved uploaded Google Drive file %s to trash during rollback.", file_id)
                except Exception as trash_error:
                    _logger.warning(
                        "Could not trash uploaded Google Drive file %s during rollback: %s",
                        file_id,
                        trash_error,
                    )


class FleetRepairDriveUploadWizardLine(models.TransientModel):
    _name = 'fleet.repair.drive.upload.wizard.line'
    _description = "Upload Fleet Repair Photo to Drive"

    wizard_id = fields.Many2one(
        'fleet.repair.drive.upload.wizard',
        required=True,
        ondelete='cascade',
    )
    image_file = fields.Binary(
        string="Imagen",
        required=True,
        attachment=False,
    )
    filename = fields.Char(string="Archivo", required=True)

    def _prepare_validated_image_file(self):
        self.ensure_one()
        filename = (self.filename or '').strip()
        if not filename:
            raise UserError(_("Todos los archivos deben tener nombre."))
        if not self.image_file:
            raise UserError(_("Debe seleccionar una imagen para %s.") % filename)

        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise UserError(_(
                "Solo se permiten imágenes jpg, jpeg, png o webp.\n"
                "Archivo no permitido: %s"
            ) % filename)

        mimetype = mimetypes.guess_type(filename)[0] or ''
        if mimetype not in ALLOWED_IMAGE_MIMETYPES:
            raise UserError(_(
                "El tipo MIME del archivo no es válido.\n"
                "Archivo no permitido: %s"
            ) % filename)

        try:
            encoded_file = self.image_file
            if isinstance(encoded_file, str):
                encoded_file = encoded_file.encode()
            file_bytes = base64.b64decode(encoded_file, validate=True)
        except (binascii.Error, ValueError):
            raise UserError(_(
                "El archivo no se pudo leer como imagen válida.\n"
                "Archivo no permitido: %s"
            ) % filename)

        detected_mimetype = self._detect_image_mimetype(file_bytes)
        if detected_mimetype not in ALLOWED_IMAGE_MIMETYPES:
            raise UserError(_(
                "El contenido real del archivo no corresponde a una imagen válida.\n"
                "Archivo no permitido: %s"
            ) % filename)
        if detected_mimetype != mimetype:
            raise UserError(_(
                "La extensión del archivo no coincide con su contenido real.\n"
                "Archivo no permitido: %s"
            ) % filename)

        return {
            'filename': filename,
            'content': file_bytes,
            'mimetype': mimetype,
        }

    def _detect_image_mimetype(self, file_bytes):
        if file_bytes.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        if file_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'image/png'
        if (
            len(file_bytes) >= 12
            and file_bytes[:4] == b'RIFF'
            and file_bytes[8:12] == b'WEBP'
        ):
            return 'image/webp'
        return False
