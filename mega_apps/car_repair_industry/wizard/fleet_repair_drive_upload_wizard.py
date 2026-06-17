# -*- coding: utf-8 -*-

import base64
import io
import mimetypes
from pathlib import Path

from odoo import fields, models, _
from odoo.exceptions import UserError


ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}


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

        drive_service = self.repair_id._drive_get_service()
        folder = self.repair_id._drive_get_or_create_repair_folder(
            drive_service,
            evidence_type=self.evidence_type,
        )

        try:
            from googleapiclient.http import MediaIoBaseUpload  # type: ignore
            from googleapiclient.errors import HttpError  # type: ignore
        except ImportError as error:
            raise UserError(_(
                "Faltan dependencias de Google Drive en Python.\n"
                "Instale:\n"
                "pip install google-api-python-client google-auth google-auth-httplib2\n\n"
                "Detalle: %s"
            ) % error)

        Evidence = self.env['fleet.repair.evidence']
        created_count = 0
        try:
            for line in self.line_ids:
                filename = line._validate_image_file()
                file_bytes = base64.b64decode(line.image_file)
                mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                media = MediaIoBaseUpload(
                    io.BytesIO(file_bytes),
                    mimetype=mimetype,
                    resumable=False,
                )
                drive_file = drive_service.files().create(
                    body={
                        'name': filename,
                        'parents': [folder['id']],
                    },
                    media_body=media,
                    fields='id, name, mimeType, webViewLink',
                    supportsAllDrives=True,
                ).execute()
                file_id = drive_file.get('id')

                Evidence.create({
                    'repair_id': self.repair_id.id,
                    'name': drive_file.get('name') or filename,
                    'evidence_type': self.evidence_type,
                    'external_url': drive_file.get('webViewLink'),
                    'drive_file_id': file_id,
                    'mime_type': drive_file.get('mimeType') or mimetype,
                    'description': self.description,
                })
                created_count += 1
        except HttpError as error:
            raise UserError(_(
                "No se pudieron subir las fotos a Google Drive.\n"
                "Verifique permisos y cuota del Drive destino.\n\n"
                "Detalle: %s"
            ) % error)
        except Exception as error:
            raise UserError(_(
                "No se pudieron subir las fotos a Google Drive.\n\n"
                "Detalle: %s"
            ) % error)

        self.line_ids.unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Google Drive"),
                'message': _("%s foto(s) subida(s) correctamente a Drive.") % created_count,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }


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

    def _validate_image_file(self):
        self.ensure_one()
        filename = self.filename or ''
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise UserError(_(
                "Solo se permiten imágenes jpg, jpeg, png o webp.\n"
                "Archivo no permitido: %s"
            ) % filename)
        if not self.image_file:
            raise UserError(_("Debe seleccionar una imagen para %s.") % filename)
        return filename
