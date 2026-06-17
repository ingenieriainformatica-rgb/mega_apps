# -*- coding: utf-8 -*-

import io
import logging

from odoo import http
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


PLACEHOLDER_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" width="400" height="260" viewBox="0 0 400 260">
<rect width="400" height="260" fill="#f3f4f6"/>
<path d="M112 168l52-56 44 46 28-30 52 40H112z" fill="#d1d5db"/>
<circle cx="270" cy="86" r="22" fill="#d1d5db"/>
<text x="200" y="218" text-anchor="middle" font-family="Arial, sans-serif" font-size="18" fill="#6b7280">Sin vista previa</text>
</svg>"""


class FleetRepairEvidenceImageController(http.Controller):
    def _placeholder_response(self, status=200):
        return request.make_response(
            PLACEHOLDER_SVG,
            headers=[
                ('Content-Type', 'image/svg+xml; charset=utf-8'),
                ('Cache-Control', 'private, max-age=60'),
            ],
            status=status,
        )

    @http.route('/car_repair/evidence/<int:evidence_id>/image', type='http', auth='user')
    def evidence_image(self, evidence_id, **kwargs):
        evidence = request.env['fleet.repair.evidence'].browse(evidence_id)
        if not evidence.exists():
            return self._placeholder_response(status=404)

        try:
            evidence.check_access('read')
        except (AccessError, MissingError):
            return self._placeholder_response(status=404)

        drive_file_id = evidence.drive_file_id or evidence._extract_drive_file_id()
        if not drive_file_id or not evidence.is_image:
            return self._placeholder_response()

        try:
            from googleapiclient.http import MediaIoBaseDownload  # type: ignore
        except ImportError:
            _logger.warning("Google Drive dependencies are not installed; evidence preview is unavailable.")
            return self._placeholder_response()

        try:
            drive_service = evidence.repair_id._drive_get_service()
            drive_request = drive_service.files().get_media(
                fileId=drive_file_id,
                supportsAllDrives=True,
            )
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, drive_request)
            done = False
            while not done:
                _status, done = downloader.next_chunk()

            return request.make_response(
                buffer.getvalue(),
                headers=[
                    ('Content-Type', evidence.mime_type or 'image/jpeg'),
                    ('Cache-Control', 'private, max-age=300'),
                ],
            )
        except UserError as error:
            _logger.warning("Google Drive evidence preview could not be loaded: %s", error)
        except Exception as error:
            _logger.warning("Google Drive evidence preview failed for evidence %s: %s", evidence.id, error)
        return self._placeholder_response()
