# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
import logging
import mimetypes
import os
from odoo import fields, models, api, _  # type: ignore
from odoo import tools  # type: ignore
from odoo.exceptions import UserError, ValidationError  # type: ignore
from markupsafe import Markup
from pathlib import Path

_logger = logging.getLogger(__name__)


MODULE_DIR = Path(__file__).resolve().parents[1]

GOOGLE_DRIVE_CREDENTIALS_PATH = (
    MODULE_DIR
    / "credentials_google_drive/"
    / "odoo-taller-drive-9cd3c29a0d22.json"
)
GOOGLE_DRIVE_ROOT_FOLDER_ID = "1AObR25Y435J2gUYXdkBkRCZRXYM_MXch"
GOOGLE_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
RENTING_PARTNER_PARAM = "car_repair_industry.renting_partner_id"
RENTING_PARTNER_NAME = "RENTING COLOMBIA S A S"
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_IMAGE_MIMETYPES = {'image/jpeg', 'image/png', 'image/webp'}


class FleetRepair(models.Model):
    _name = 'fleet.repair'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Car Repair"
    _order = 'id desc'

    name = fields.Char(string='Concepto', required=True)
    sequence = fields.Char(string='Sequence', readonly=True, copy=False)
    client_id = fields.Many2one('res.partner', string='Client', required=True, tracking=True)
    client_phone = fields.Char(string='Phone')
    client_mobile = fields.Char(string='Mobile')
    client_email = fields.Char(string='Email')
    receipt_date = fields.Date(string='Date of Receipt', default=lambda self: fields.Date.context_today(self),)
    contact_name = fields.Char(string='Contact Name')
    phone = fields.Char(string='Contact Number')
    customer_type = fields.Selection(
        [
            ('renting', 'Renting'),
            ('particular', '1a1'),
            ('corporate', 'MegaSur'),
        ],
        string="Sede",
        default='particular',
        required=True,
        tracking=True,
    )
    renting_reference = fields.Char(string="CI / referencia Renting", copy=False)
    renting_appointment_validated = fields.Boolean(string="Cita Renting validada", copy=False)
    delivered_by_name = fields.Char(string="Persona que entrega", copy=False)
    delivered_by_phone = fields.Char(string="Celular quien entrega", copy=False)
    delivered_by_document = fields.Char(string="Documento quien entrega", copy=False)
    delivered_by_email = fields.Char(string="Correo quien entrega", copy=False)
    delivered_by_observation = fields.Text(string="Observaciones persona que entrega", copy=False)
    reception_mileage = fields.Float(string="Kilometraje recepción", copy=False)
    reception_fuel_level = fields.Selection(
        [
            ('empty', 'Vacío'),
            ('reserve', 'Reserva'),
            ('quarter', '1/4'),
            ('half', '1/2'),
            ('three_quarters', '3/4'),
            ('full', 'Lleno'),
        ],
        string="Nivel de combustible recepción",
        copy=False,
    )
    valuables_inside = fields.Selection(
        [
            ('yes', 'Sí'),
            ('no', 'No'),
        ],
        string="Tiene objetos de valor",
        copy=False,
    )
    valuables_description = fields.Text(string="Pertenencias / objetos de valor", copy=False)
    received_documents = fields.Text(string="Documentos recibidos", copy=False)
    reception_general_observations = fields.Text(string="Observaciones generales de recepción", copy=False)
    fleet_id = fields.Many2one('fleet.vehicle', 'Car')
    license_plate = fields.Char('License Plate',
                                help='License plate number of the vehicle (ie: plate number for a car)')
    vin_sn = fields.Char('Chassis Number', help='Unique number written on the vehicle motor (VIN/SN number)')
    model_id = fields.Many2one('fleet.vehicle.model', 'Model', help='Model of the vehicle')
    vehicle_brand_id = fields.Many2one(
        'fleet.vehicle.model.brand',
        string='Marca',
        help='Marca del vehículo (filtra la lista de líneas/modelos).',
        copy=False,
    )
    model_year = fields.Char(
        string='Modelo (año)',
        size=4,
        copy=False,
        help='Año del modelo del vehículo (ej. 2017).',
    )
    engine_displacement = fields.Char(
        string='Cilindraje',
        size=8,
        copy=False,
        help='Cilindraje del motor en cc (ej. 1998).',
    )
    engine_number = fields.Char(
        string='Número de motor',
        size=64,
        copy=False,
        help='Número de motor del vehículo.',
    )
    fuel_type = fields.Selection([('diesel', 'Diesel'),
                                  ('gasoline', 'Gasoline'),
                                  ('full_hybrid', 'Full Hybrid'),
                                  ('plug_in_hybrid_diesel', 'Plug-in Hybrid Diesel'),
                                  ('plug_in_hybrid_gasoline', 'Plug-in Hybrid Gasoline'),
                                  ('cng', 'CNG'),
                                  ('lpg', 'LPG'),
                                  ('hydrogen', 'Hydrogen'),
                                  ('electric', 'Electric'), ('hybrid', 'Hybrid')], 'Fuel Type',
                                 help='Fuel Used by the vehicle')
    guarantee = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Under Guarantee?')
    guarantee_type = fields.Selection(
        [('paid', 'paid'), ('free', 'Free')], string='Guarantee Type')
    service_type = fields.Many2one('service.type', string='Nature of Service')
    user_id = fields.Many2one('res.users', string='Assigned to', tracking=True)
    portal_advisor_id = fields.Many2one(
        'res.users',
        string="Asesor recepción",
        tracking=True,
        copy=False,
    )
    portal_technician_id = fields.Many2one(
        'res.users',
        string="Técnico portal",
        tracking=True,
        copy=False,
    )
    road_test_user_id = fields.Many2one(
        'res.users',
        string="Responsable prueba de ruta",
        tracking=True,
        copy=False,
    )
    purchase_quote_user_id = fields.Many2one(
        'res.users',
        string="Asesor compras/cotizaciones",
        tracking=True,
        copy=False,
    )
    service_flow_state = fields.Selection(
        [
            ('received', 'Recibido'),
            ('to_assign', 'Por asignar'),
            ('assigned', 'Asignado'),
            ('diagnosis', 'En diagnóstico'),
            ('diagnosis_done', 'Diagnóstico finalizado'),
            ('road_test_requested', 'Prueba de ruta solicitada'),
            ('road_test', 'En prueba de ruta'),
            ('road_test_done', 'Prueba de ruta finalizada'),
            ('purchase_requested', 'Remitido a compras/cotizaciones'),
            ('quote_ready', 'Cotización lista'),
            ('quote_sent', 'Cotización enviada'),
            ('approved', 'Aprobado'),
            ('repair', 'En reparación'),
            ('ready_delivery', 'Listo para entrega'),
            ('delivered', 'Entregado'),
            ('cancelled', 'Cancelado'),
        ],
        string="Flujo operativo",
        default='received',
        tracking=True,
        copy=False,
        index=True,
    )
    technician_started_at = fields.Datetime(string="Inicio técnico", readonly=True, copy=False)
    technician_finished_at = fields.Datetime(string="Fin técnico", readonly=True, copy=False)
    road_test_requested_at = fields.Datetime(string="Solicitud prueba ruta", readonly=True, copy=False)
    road_test_started_at = fields.Datetime(string="Inicio prueba ruta", readonly=True, copy=False)
    road_test_finished_at = fields.Datetime(string="Fin prueba ruta", readonly=True, copy=False)
    sent_to_purchase_at = fields.Datetime(string="Remitido a compras", readonly=True, copy=False)
    technical_observation = fields.Text(string="Observación técnica")
    requested_materials = fields.Text(string="Materiales/repuestos requeridos")
    road_test_result = fields.Text(string="Resultado prueba de ruta")
    purchase_quote_note = fields.Text(string="Nota compras/cotizaciones")
    closure_result = fields.Selection(
        [
            ('finished_ok', 'Finalizado correctamente'),
            ('requires_road_test', 'Requiere prueba de ruta'),
            ('pending_customer', 'Pendiente por cliente'),
            ('rescheduled', 'Reprogramado'),
            ('not_possible', 'No fue posible'),
            ('requires_quote', 'Requiere cotización'),
        ],
        string="Resultado de cierre",
        copy=False,
        tracking=True,
    )
    priority = fields.Selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High')], 'Priority')
    description = fields.Text(string='Notes')
    service_detail = fields.Text(string='Service Details')
    state = fields.Selection([
        ('draft', 'Received'),
        ('diagnosis', 'In Diagnosis'),
        ('diagnosis_complete', 'Diagnosis Complete'),
        ('quote', 'Quotation Sent'),
        ('saleorder', 'Quotation Approved'),
        ('workorder', 'Work in Progress'),
        ('work_completed', 'Work Completed'),
        ('invoiced', 'Invoiced'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], 'Status', default="draft", readonly=True, copy=False, help="Gives the status of the fleet repairing.",
        index=True, tracking=True)
    diagnose_id = fields.Many2one('fleet.diagnose', string='Car Diagnose', copy=False)
    workorder_id = fields.Many2one('fleet.workorder', string='Car Work Order', copy=False)
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', copy=False)
    fleet_repair_line = fields.One2many('fleet.repair.line', 'fleet_repair_id', string="Car Lines")
    workorder_count = fields.Integer(string='Work Orders', compute='_compute_workorder_id')
    dig_count = fields.Integer(string='Diagnosis Orders', compute='_compute_dignosis_id')
    quotation_count = fields.Integer(string="Quotations", compute='_compute_quotation_id')
    saleorder_count = fields.Integer(string="Sale Order", compute='_compute_saleorder_id')
    inv_count = fields.Integer(string="Invoice")
    confirm_sale_order = fields.Boolean('is confirm')
    images_ids = fields.One2many('ir.attachment', 'car_repair_id', 'Images')
    external_evidence_ids = fields.One2many(
        'fleet.repair.evidence',
        'repair_id',
        string="Evidencias externas",
    )
    parent_id = fields.Many2one('fleet.repair', string='Parent Repair', index=True)

    child_ids = fields.One2many('fleet.repair', 'parent_id', string="Sub-Repair")
    road_test_ids = fields.One2many('fleet.road.test', 'repair_id', string='Pruebas de ruta')

    repair_checklist_ids = fields.Many2many('fleet.repair.checklist', 'checkbox_checklist_rel',
                                            'id', 'checklist_id',
                                            string='Repair Checklist')
    reception_checklist_template_id = fields.Many2one(
        'fleet.repair.reception.checklist.template',
        string="Plantilla de checklist de recepción",
        tracking=True,
        help="Plantilla del checklist diligenciado por el asesor en la recepción. "
             "Solo afecta a las líneas con tipo 'asesor'.",
    )
    reception_checklist_line_ids = fields.One2many(
        'fleet.repair.reception.checklist.line',
        'repair_id',
        string="Checklist de recepción (asesor)",
        copy=True,
        domain=[('checklist_type', '=', 'asesor')],
    )
    technical_checklist_template_id = fields.Many2one(
        'fleet.repair.reception.checklist.template',
        string="Plantilla de checklist técnico",
        tracking=True,
        help="Plantilla del checklist diligenciado por el técnico durante el diagnóstico / reparación. "
             "Solo afecta a las líneas con tipo 'tecnico'.",
    )
    technical_checklist_line_ids = fields.One2many(
        'fleet.repair.reception.checklist.line',
        'repair_id',
        string="Checklist técnico",
        copy=True,
        domain=[('checklist_type', '=', 'tecnico')],
    )
    feedback_description = fields.Char(string="Feedback")
    rating = fields.Selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High')], string="Rating")
    timesheet_ids = fields.One2many('account.analytic.line', 'repair_id', string="Timesheet")
    planned_hours = fields.Float("Initially Planned Hours", tracking=True)
    subtask_planned_hours = fields.Float("Sub-tasks Planned Hours", compute='_compute_subtask_planned_hours',
                                         help="Sum of the hours allocated for all the sub-tasks (and their own sub-tasks) linked to this task. Usually less than or equal to the allocated hours of this task.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            customer_type = vals.get('customer_type', 'particular')
            vals['sequence'] = self.env['fleet.repair.branch'].get_next_for_customer_type(customer_type)
        return super(FleetRepair, self).create(vals_list)

    @api.depends('child_ids.planned_hours')
    def _compute_subtask_planned_hours(self):
        for task in self:
            task.subtask_planned_hours = sum(
                child_task.planned_hours + child_task.subtask_planned_hours for child_task in task.child_ids)

    @api.onchange('reception_checklist_template_id')
    def _onchange_reception_checklist_template_id(self):
        template = self.reception_checklist_template_id
        existing_asesor_ids = self.reception_checklist_line_ids.filtered(
            lambda l: l.checklist_type == 'asesor'
        ).ids
        operations = [(2, line_id, 0) for line_id in existing_asesor_ids]
        if not template:
            self.reception_checklist_line_ids = operations
            return
        for item in template.line_ids.filtered('active'):
            operations.append((0, 0, {
                'sequence': item.sequence,
                'template_id': template.id,
                'template_line_id': item.id,
                'name': item.name,
                'checklist_type': 'asesor',
            }))
        self.reception_checklist_line_ids = operations

    @api.onchange('technical_checklist_template_id')
    def _onchange_technical_checklist_template_id(self):
        template = self.technical_checklist_template_id
        existing_tecnico_ids = self.reception_checklist_line_ids.filtered(
            lambda l: l.checklist_type == 'tecnico'
        ).ids
        operations = [(2, line_id, 0) for line_id in existing_tecnico_ids]
        if not template:
            self.reception_checklist_line_ids = operations
            return
        for item in template.line_ids.filtered('active'):
            operations.append((0, 0, {
                'sequence': item.sequence,
                'template_id': template.id,
                'template_line_id': item.id,
                'name': item.name,
                'checklist_type': 'tecnico',
            }))
        self.reception_checklist_line_ids = operations

    def _drive_get_google_modules(self):
        try:
            from google.oauth2 import service_account  # type: ignore
            from googleapiclient.discovery import build  # type: ignore
            from googleapiclient.errors import HttpError  # type: ignore
        except ImportError as error:
            raise UserError(_(
                "Faltan dependencias de Google Drive en Python.\n"
                "Instale:\n"
                "pip install google-api-python-client google-auth google-auth-httplib2\n\n"
                "Detalle: %s"
            ) % error)
        return service_account, build, HttpError

    def _drive_get_service(self):
        service_account, build, HttpError = self._drive_get_google_modules()
        if not os.path.exists(GOOGLE_DRIVE_CREDENTIALS_PATH):
            raise UserError(_(
                "No se encontró el archivo de credenciales de Google Drive en:\n%s"
            ) % GOOGLE_DRIVE_CREDENTIALS_PATH)

        try:
            credentials = service_account.Credentials.from_service_account_file(
                GOOGLE_DRIVE_CREDENTIALS_PATH,
                scopes=GOOGLE_DRIVE_SCOPES,
            )
            return build(
                'drive',
                'v3',
                credentials=credentials,
                cache_discovery=False,
            )
        except Exception as error:
            raise UserError(_(
                "No se pudo autenticar con Google Drive.\n\n"
                "Detalle: %s"
            ) % error)

    def _drive_check_root_folder_access(self, drive_service):
        try:
            return drive_service.files().get(
                fileId=GOOGLE_DRIVE_ROOT_FOLDER_ID,
                fields='id, name, webViewLink',
                supportsAllDrives=True,
            ).execute()
        except Exception as error:
            raise UserError(_(
                "No se pudo acceder a la carpeta raíz de Google Drive.\n"
                "Verifique que esté compartida con la Service Account.\n\n"
                "Detalle: %s"
            ) % error)

    def _drive_escape_query_value(self, value):
        return (value or '').replace("\\", "\\\\").replace("'", "\\'")

    def _drive_get_repair_folder_name(self, evidence_type=False):
        self.ensure_one()
        folder_name = self.sequence or self.display_name
        if self.license_plate:
            folder_name = "%s - %s" % (folder_name, self.license_plate)
        evidence_labels = {
            'recepcion': _("Recepción"),
            'diagnostico': _("Diagnóstico"),
            'reparacion': _("Reparación"),
            'entrega': _("Entrega"),
            'otro': _("Otro"),
        }
        if evidence_type:
            folder_name = "%s - %s" % (
                folder_name,
                evidence_labels.get(evidence_type, evidence_type),  #type: ignore
            )
        return folder_name

    def _drive_get_or_create_child_folder(self, drive_service, parent_id, folder_name):
        escaped_name = self._drive_escape_query_value(folder_name)
        query = (
            "mimeType = 'application/vnd.google-apps.folder' "
            "and name = '%s' "
            "and '%s' in parents "
            "and trashed = false"
        ) % (escaped_name, parent_id)
        folder_list = drive_service.files().list(
            q=query,
            fields='files(id, name, webViewLink)',
            pageSize=1,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        folders = folder_list.get('files', [])
        if folders:
            return folders[0]

        return drive_service.files().create(
            body={
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id],
            },
            fields='id, name, webViewLink',
            supportsAllDrives=True,
        ).execute()

    def _drive_get_or_create_repair_folder(self, drive_service, evidence_type=False):
        self.ensure_one()
        self._drive_check_root_folder_access(drive_service)
        year = str((self.receipt_date or fields.Date.context_today(self)).year)
        year_folder = self._drive_get_or_create_child_folder(
            drive_service,
            GOOGLE_DRIVE_ROOT_FOLDER_ID,
            year,
        )
        repair_folder = self._drive_get_or_create_child_folder(
            drive_service,
            year_folder['id'],
            self._drive_get_repair_folder_name(),
        )
        if not evidence_type:
            return repair_folder
        evidence_labels = {
            'recepcion': _("Recepción"),
            'diagnostico': _("Diagnóstico"),
            'reparacion': _("Reparación"),
            'entrega': _("Entrega"),
            'otro': _("Otro"),
        }
        return self._drive_get_or_create_child_folder(
            drive_service,
            repair_folder['id'],
            evidence_labels.get(evidence_type, evidence_type),  # type: ignore
        )

    def _search_renting_partner(self):
        parameters = self.env['ir.config_parameter'].sudo()
        partner_id = parameters.get_param(RENTING_PARTNER_PARAM)
        partner = self.env['res.partner'].sudo().browse(int(partner_id or 0))
        if partner.exists():
            return partner
        partner = self.env['res.partner'].sudo().search([
            ('name', '=ilike', RENTING_PARTNER_NAME),
            ('is_company', '=', True),
        ], limit=1)
        if partner:
            parameters.set_param(RENTING_PARTNER_PARAM, partner.id)
        return partner if partner.exists() else self.env['res.partner']

    def _get_renting_partner(self):
        partner = self._search_renting_partner()
        if not partner.exists():
            raise UserError(_(
                "No se encontró el contacto empresarial '%s'.\n"
                "Créelo o configure el parámetro del sistema %s con su ID."
            ) % (RENTING_PARTNER_NAME, RENTING_PARTNER_PARAM))
        return partner

    def _find_renting_partner(self):
        return self._search_renting_partner()

    def _drive_prepare_image_file(self, filename, file_bytes, mimetype=False):
        filename = (filename or '').strip()
        if not filename:
            raise UserError(_("Todos los archivos deben tener nombre."))
        if not file_bytes:
            raise UserError(_("El archivo %s está vacío.") % filename)

        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise UserError(_(
                "Solo se permiten imágenes jpg, jpeg, png o webp.\n"
                "Archivo no permitido: %s"
            ) % filename)

        guessed_mimetype = mimetype or mimetypes.guess_type(filename)[0] or ''
        if guessed_mimetype not in ALLOWED_IMAGE_MIMETYPES:
            raise UserError(_(
                "El tipo MIME del archivo no es válido.\n"
                "Archivo no permitido: %s"
            ) % filename)

        detected_mimetype = self._drive_detect_image_mimetype(file_bytes)
        if detected_mimetype not in ALLOWED_IMAGE_MIMETYPES:
            raise UserError(_(
                "El contenido real del archivo no corresponde a una imagen válida.\n"
                "Archivo no permitido: %s"
            ) % filename)
        if detected_mimetype != guessed_mimetype:
            raise UserError(_(
                "La extensión del archivo no coincide con su contenido real.\n"
                "Archivo no permitido: %s"
            ) % filename)

        return {
            'filename': filename,
            'content': file_bytes,
            'mimetype': guessed_mimetype,
        }

    def _drive_detect_image_mimetype(self, file_bytes):
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

    def _drive_rollback_uploaded_files(self, drive_service, uploaded_files):
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

    def _drive_upload_evidence_images(self, files, evidence_type='recepcion', description=False):
        self.ensure_one()
        if not files:
            return self.env['fleet.repair.evidence']

        try:
            from googleapiclient.http import MediaIoBaseUpload  # type: ignore
        except ImportError as error:
            raise UserError(_(
                "Faltan dependencias de Google Drive en Python.\n"
                "Instale:\n"
                "pip install google-api-python-client google-auth google-auth-httplib2\n\n"
                "Detalle: %s"
            ) % error)

        drive_service = self._drive_get_service()
        _, _, HttpError = self._drive_get_google_modules()
        folder = self._drive_get_or_create_repair_folder(
            drive_service,
            evidence_type=evidence_type,
        )
        Evidence = self.env['fleet.repair.evidence']
        uploaded_files = []
        evidences = Evidence.browse()
        try:
            for file_data in files:
                from io import BytesIO
                media = MediaIoBaseUpload(
                    BytesIO(file_data['content']),
                    mimetype=file_data['mimetype'],
                    resumable=False,
                )
                drive_file = drive_service.files().create(
                    body={
                        'name': file_data['filename'],
                        'parents': [folder['id']],
                    },
                    media_body=media,
                    fields='id, name, mimeType, webViewLink',
                    supportsAllDrives=True,
                ).execute()
                drive_file['evidence_category'] = file_data.get('evidence_category') or 'otro'
                uploaded_files.append(drive_file)

            for drive_file in uploaded_files:
                evidences |= Evidence.create({
                    'repair_id': self.id,
                    'name': drive_file.get('name'),
                    'evidence_type': evidence_type,
                    'evidence_category': drive_file.get('evidence_category') or 'otro',
                    'external_url': drive_file.get('webViewLink'),
                    'drive_file_id': drive_file.get('id'),
                    'mime_type': drive_file.get('mimeType'),
                    'description': description,
                })
        except HttpError as error:
            self._drive_rollback_uploaded_files(drive_service, uploaded_files)
            raise UserError(_(
                "No se pudieron subir las fotos a Google Drive.\n"
                "Verifique permisos y cuota del Drive destino.\n\n"
                "Detalle: %s"
            ) % error)
        except Exception as error:
            self._drive_rollback_uploaded_files(drive_service, uploaded_files)
            raise UserError(_(
                "No se pudieron subir las fotos a Google Drive.\n\n"
                "Detalle: %s"
            ) % error)
        return evidences

    def button_view_diagnosis(self):
        list = []
        context = dict(self._context or {})
        dig_order_ids = self.env['fleet.diagnose'].search([('fleet_repair_id', '=', self.id)])
        for order in dig_order_ids:
            list.append(order.id)
        return {
            'name': _('Car Diagnosis'),
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': 'fleet.diagnose',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', list)],
            'context': context,
        }

    def button_view_workorder(self):
        list = []
        context = dict(self._context or {})
        work_order_ids = self.env['fleet.workorder'].search([('fleet_repair_id', '=', self.id)])
        for order in work_order_ids:
            list.append(order.id)
        return {
            'name': _('Car Work Order'),
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': 'fleet.workorder',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', list)],
            'context': context,
        }

    def button_view_quotation(self):
        list = []
        context = dict(self._context or {})
        quo_order_ids = self.env['sale.order'].search([('state', '=', 'draft'), ('fleet_repair_id', '=', self.id)])
        for order in quo_order_ids:
            list.append(order.id)
        return {
            'name': _('Sale'),
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': 'sale.order',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', list)],
            'context': context,
        }

    def button_view_saleorder(self):
        list = []
        context = dict(self._context or {})
        quo_order_ids = self.env['sale.order'].search([('state', '=', 'sale'), ('fleet_repair_id', '=', self.id)])
        for order in quo_order_ids:
            list.append(order.id)
        return {
            'name': _('Sale'),
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': 'sale.order',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', list)],
            'context': context,
        }

    def button_view_invoice(self):
        list = []
        inv_list = []
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('account.action_invoice_tree1')
        list_view_id = imd.xmlid_to_res_id('account.invoice_tree')
        form_view_id = imd.xmlid_to_res_id('account.invoice_form')
        so_order_ids = self.env['sale.order'].search([('state', '=', 'sale'), ('fleet_repair_id', '=', self.id)])
        for order in so_order_ids:
            inv_order_ids = self.env['account.move'].search([('origin', '=', order.name)])
            if inv_order_ids:
                for order_id in inv_order_ids:
                    if order_id.id not in list:
                        list.append(order_id.id)

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'list'], [form_view_id, 'form'], [False, 'graph'], [False, 'kanban'],
                      [False, 'calendar'], [False, 'pivot']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(list) > 1:
            result['domain'] = "[('id','in',%s)]" % list
        elif len(list) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = list[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    @api.depends('workorder_id')
    def _compute_workorder_id(self):
        for order in self:
            work_order_ids = self.env['fleet.workorder'].search([('fleet_repair_id', '=', order.id)])
            order.workorder_count = len(work_order_ids)

    @api.depends('diagnose_id')
    def _compute_dignosis_id(self):
        for order in self:
            dig_order_ids = self.env['fleet.diagnose'].search([('fleet_repair_id', '=', order.id)])
            order.dig_count = len(dig_order_ids)

    @api.depends('sale_order_id')
    def _compute_quotation_id(self):
        for order in self:
            quo_order_ids = self.env['sale.order'].search([('state', '=', 'draft'), ('fleet_repair_id', '=', order.id)])
            order.quotation_count = len(quo_order_ids)

    @api.depends('confirm_sale_order')
    def _compute_saleorder_id(self):
        for order in self:
            order.quotation_count = 0
            so_order_ids = self.env['sale.order'].search([('state', '=', 'sale'), ('fleet_repair_id', '=', order.id)])
            order.saleorder_count = len(so_order_ids)

    @api.depends('state')
    def _compute_invoice_id(self):
        count = 0
        if self.state == 'invoiced':
            for order in self:
                so_order_ids = self.env['sale.order'].search(
                    [('state', '=', 'sale'), ('fleet_repair_id', '=', order.id)])
                for order in so_order_ids:
                    inv_order_ids = self.env['account.move'].search([('origin', '=', order.name)])
                    if inv_order_ids:
                        self.inv_count = len(inv_order_ids)

    def diagnosis_created(self):
        self.write({'state': 'diagnosis'})

    def quote_created(self):
        self.write({'state': 'quote'})

    def order_confirm(self):
        self.write({'state': 'saleorder'})

    def fleet_confirmed(self):
        self.write({'state': 'confirm'})

    def workorder_created(self):
        self.write({'state': 'workorder'})

    def _notify_repair_group(self, group_xmlid, summary, note=False):
        group = self.env.ref(group_xmlid, raise_if_not_found=False)
        if not group:
            return
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        for repair in self:
            users = group.users.filtered(lambda user: user.active and not user.share)
            for user in users:
                repair.activity_schedule(
                    activity_type_id=activity_type.id if activity_type else False,
                    user_id=user.id,
                    summary=summary,
                    note=note or summary,
                )

    def _notify_repair_user(self, user, summary, note=False):
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        for repair in self:
            if user and user.active:
                repair.activity_schedule(
                    activity_type_id=activity_type.id if activity_type else False,
                    user_id=user.id,
                    summary=summary,
                    note=note or summary,
                )

    def get_service_flow_state_label(self):
        self.ensure_one()
        return dict(self._fields['service_flow_state'].selection).get(self.service_flow_state, self.service_flow_state)

    _STATE_LABELS_ES = {
        'draft':              'Recibido',
        'diagnosis':          'En diagnóstico',
        'diagnosis_complete': 'Diagnóstico completo',
        'quote':              'Cotización enviada',
        'saleorder':          'Cotización aprobada',
        'workorder':          'En reparación',
        'work_completed':     'Trabajo completado',
        'invoiced':           'Facturado',
        'done':               'Finalizado',
        'cancel':             'Cancelado',
    }

    def get_state_label(self):
        self.ensure_one()
        return self._STATE_LABELS_ES.get(self.state, self.state or '')

    def action_flow_mark_to_assign(self):
        self.write({'service_flow_state': 'to_assign'})
        self._notify_repair_group(
            'car_repair_industry.group_fleet_repair_service_manager',
            _("Nueva orden por asignar"),
        )
        return True

    def action_flow_assign_technician(self):
        for repair in self:
            technician = repair.portal_technician_id or repair.user_id
            if not technician:
                raise UserError(_("Debe asignar un técnico antes de continuar."))
            repair.write({
                'user_id': technician.id,
                'portal_technician_id': technician.id,
                'service_flow_state': 'assigned',
            })
            repair._notify_repair_user(
                technician,
                _("Se le asignó una orden de servicio"),
                _("Orden: %s") % (repair.sequence or repair.display_name),
            )
        return True

    def action_reassign_technician(self):
        """Opens the technician reassignment wizard from the repair order form."""
        self.ensure_one()
        if not self.diagnose_id:
            raise UserError(_("Esta orden no tiene un diagnóstico relacionado."))
        action = self.env['ir.actions.act_window']._for_xml_id(
            'car_repair_industry.action_fleet_diagnose_assign_to_technician'
        )
        action['context'] = {
            'is_reassignment': True,
            'active_id': self.diagnose_id.id,
            'active_model': 'fleet.diagnose',
        }
        return action

    def action_flow_start_technician(self):
        self.write({
            'service_flow_state': 'diagnosis',
            'technician_started_at': fields.Datetime.now(),
        })
        return True

    def action_flow_request_road_test(self):
        self.write({
            'service_flow_state': 'road_test_requested',
            'road_test_requested_at': fields.Datetime.now(),
            'closure_result': 'requires_road_test',
        })
        self._notify_repair_group(
            'car_repair_industry.group_fleet_repair_service_manager',
            _("Solicitud de prueba de ruta"),
        )
        for repair in self:
            repair._notify_repair_user(
                repair.road_test_user_id,
                _("Se le asignó una prueba de ruta"),
                _("Orden: %s") % (repair.sequence or repair.display_name),
            )
        return True

    def action_flow_start_road_test(self):
        self.write({
            'service_flow_state': 'road_test',
            'road_test_started_at': fields.Datetime.now(),
        })
        return True

    def action_flow_finish_road_test(self):
        self.write({
            'service_flow_state': 'road_test_done',
            'road_test_finished_at': fields.Datetime.now(),
        })
        self._notify_repair_group(
            'car_repair_industry.group_fleet_repair_service_manager',
            _("Prueba de ruta finalizada"),
        )
        return True

    def action_flow_send_to_purchase(self):
        self.write({
            'service_flow_state': 'purchase_requested',
            'sent_to_purchase_at': fields.Datetime.now(),
            'technician_finished_at': fields.Datetime.now(),
            'closure_result': 'requires_quote',
        })
        self._notify_repair_group(
            'car_repair_industry.group_fleet_repair_directeur_commercial',
            _("Orden remitida a compras/cotizaciones"),
        )
        return True

    def action_flow_quote_ready(self):
        self.write({'service_flow_state': 'quote_ready'})
        for repair in self:
            repair._notify_repair_user(
                repair.portal_advisor_id,
                _("Cotización lista para enviar al cliente"),
                _("Orden: %s") % (repair.sequence or repair.display_name),
            )
        return True

    @api.onchange('client_id')
    def onchange_partner_id(self):
        addr = {}
        if self.client_id:
            addr = self.client_id.address_get(['contact'])
            addr['client_phone'] = self.client_id.phone
            addr['client_mobile'] = self.client_id.phone
            addr['client_email'] = self.client_id.email
            self.contact_name = self.client_id.name
        return {'value': addr}

    def action_create_fleet_diagnosis(self):
        Diagnosis_obj = self.env['fleet.diagnose']
        fleet_line_obj = self.env['fleet.repair.line']
        timesheet_obj = self.env['account.analytic.line']
        repair_obj = self.env['fleet.repair'].browse(self._ids[0])
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']
        if not repair_obj.fleet_repair_line:
            raise UserError(_('You cannot create Car Diagnosis without Cars.'))

        diagnose_vals = {
            'service_rec_no': repair_obj.sequence,
            'name': repair_obj.name,
            'priority': repair_obj.priority,
            'receipt_date': repair_obj.receipt_date,
            'client_id': repair_obj.client_id.id,
            'contact_name': repair_obj.contact_name,
            'phone': repair_obj.phone,
            'client_phone': repair_obj.client_phone,
            'client_mobile': repair_obj.client_mobile,
            'client_email': repair_obj.client_email,
            'fleet_repair_id': repair_obj.id,
            'state': 'draft',
        }
        diagnose_id = Diagnosis_obj.create(diagnose_vals)
        for line in repair_obj.fleet_repair_line:
            fleet_line_vals = {
                'fleet_id': line.fleet_id.id,
                'license_plate': line.license_plate,
                'vin_sn': line.vin_sn,
                'fuel_type': line.fuel_type,
                'model_id': line.model_id.id,
                'service_type': line.service_type.id,
                'guarantee': line.guarantee,
                'guarantee_type': line.guarantee_type,
                'service_detail': line.service_detail,
                'diagnose_id': diagnose_id.id,
                'list_of_damage': line.list_of_damage,
                'car_year': line.car_year,
                'diagnose_id': diagnose_id.id,
                'state': 'diagnosis',
                'source_line_id': line.id,
            }
            fleet_line_obj.create(fleet_line_vals)
            line.write({'state': 'diagnosis'})

        for rec in repair_obj.timesheet_ids:
            timesheet_line_vals = {
                'date': rec.date,
                'diagnose_id': diagnose_id.id,
                'project_id': rec.project_id.id,
                'name': rec.name,
                'service_type': rec.service_type.id,
                'unit_amount': rec.unit_amount,
                'company_id': rec.company_id.id,
                'currency_id': rec.currency_id.id,

            }
            timesheet_obj.create(timesheet_line_vals)

        self.write({'state': 'diagnosis', 'diagnose_id': diagnose_id.id})
        result = mod_obj._xmlid_lookup("%s.%s" % ('car_repair_industry', 'action_fleet_diagnose_tree_view'))
        id = result and result[1] or False
        result = act_obj.browse(id).read()[0]
        res = mod_obj._xmlid_lookup("%s.%s" % ('car_repair_industry', 'view_fleet_diagnose_form'))
        result['views'] = [(res and res[1] or False, 'form')]
        result['res_id'] = diagnose_id.id or False
        return result

    def action_test_google_drive_connection(self):
        self.ensure_one()
        if not (
            self.env.user.has_group('car_repair_industry.group_fleet_repair_service_manager')
            or self.env.user.has_group('base.group_system')
        ):
            raise UserError("No tiene permisos para ejecutar esta prueba.")

        folder_name = "TEST ODOO DRIVE - %s" % (self.sequence or self.name or self.display_name)

        drive_service = self._drive_get_service()
        self._drive_check_root_folder_access(drive_service)
        _, _, HttpError = self._drive_get_google_modules()
        try:
            folder = drive_service.files().create(
                body={
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [GOOGLE_DRIVE_ROOT_FOLDER_ID],
                },
                fields='id, webViewLink',
                supportsAllDrives=True,
            ).execute()

            self.env['fleet.repair.evidence'].create({
                'repair_id': self.id,
                'name': folder_name,
                'evidence_type': 'otro',
                'external_url': folder.get('webViewLink'),
                'description': _("Prueba técnica de conexión con Google Drive."),
            })
        except HttpError as error:
            raise UserError(_(
                "No se pudo completar la prueba de Google Drive.\n"
                "Verifique que la carpeta raíz esté compartida con la Service Account.\n\n"
                "Detalle: %s"
            ) % error)
        except Exception as error:
            raise UserError(_(
                "No se pudo completar la prueba de Google Drive.\n\n"
                "Detalle: %s"
            ) % error)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Google Drive"),
                'message': _("Prueba completada. Se creó la carpeta de prueba."),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_open_drive_upload_wizard(self):
        self.ensure_one()
        return {
            'name': _("Subir fotos a Drive"),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.repair.drive.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_repair_id': self.id,
            },
        }

    def action_print_receipt(self):
        assert len(self._ids) == 1, 'This option should only be used for a single id at a time'
        return self.env.ref('car_repair_industry.fleet_repair_receipt_id').report_action(self)

    def action_print_label(self):
        if not self.fleet_repair_line:
            raise UserError(_('You cannot print report without Car details'))

        assert len(self._ids) == 1, 'This option should only be used for a single id at a time'
        return self.env.ref('car_repair_industry.fleet_repair_label_id').report_action(self)

    def action_view_quotation(self):
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']
        order_id = self.sale_order_id.id
        result = mod_obj._xmlid_lookup("%s.%s" % ('sale', 'action_orders'))[1:3]
        id = result and result[1] or False
        result = act_obj.browse(id).read()[0]
        res = mod_obj._xmlid_lookup("%s.%s" % ('sale', 'view_order_form'))[1:3]
        result['views'] = [(res and res[1] or False, 'form')]
        result['res_id'] = order_id or False
        return result

    def action_view_work_order(self):
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']
        work_order_id = self.workorder_id.id
        result = mod_obj._xmlid_lookup("%s.%s" % ('car_repair_industry', 'action_fleet_workorder_tree_view'))[1:3]
        id = result and result[1] or False
        result = act_obj.browse(id).read()[0]
        res = mod_obj._xmlid_lookup("%s.%s" % ('car_repair_industry', 'view_fleet_workorder_form'))[1:3]
        result['views'] = [(res and res[1] or False, 'form')]
        result['res_id'] = work_order_id or False
        return result

    @api.model
    def action_activity_dashboard_redirect(self):
        if self.env.user.has_group('base.group_user'):
            return self.env["ir.actions.actions"]._for_xml_id("car_repair_industry.fleet_repair_dashboard")
        return self.env["ir.actions.actions"]._for_xml_id("car_repair_industry.fleet_repair_dashboard")

    def write(self, vals):
        images_changed = "images_ids" in vals and not self.env.is_superuser()

        # 1) Antes de escribir, guardamos las imágenes actuales por registro
        old_attachments_map = {}
        if images_changed:
            for rec in self:
                old_attachments_map[rec.id] = set(rec.images_ids.ids)

            commands = vals["images_ids"]
            if not isinstance(commands, (list, tuple)):
                commands = [commands]

            remove_command_detected = False

            for cmd in commands:
                # cmd es una tupla/lista tipo (op, id, vals)
                if not isinstance(cmd, (list, tuple)) or not cmd:
                    continue
                op = cmd[0]

                # 3 = unlink relación, 5 = limpiar todas, 6 = reemplazar lista
                if op in (3, 5, 6):
                    remove_command_detected = True
                    break

            if remove_command_detected and not self.env.user.has_group(
                "car_repair_industry.group_taller_delete_images"
            ):
                raise UserError(
                    _(
                        "No tiene permisos para eliminar imágenes de diagnósticos de taller."
                    )
                )

        # 2) Ejecutamos el write real
        res = super().write(vals)

        # 3) Después del write, detectamos qué imágenes fueron eliminadas
        if images_changed:
            Attachment = self.env["ir.attachment"]
            user_name = self.env.user.display_name

            for rec in self:
                old_ids = old_attachments_map.get(rec.id, set())
                new_ids = set(rec.images_ids.ids)
                removed_ids = old_ids - new_ids

                if removed_ids:
                    removed_attachments = Attachment.browse(list(removed_ids))
                    names = ", ".join(removed_attachments.mapped("name"))
                    # Mensaje en el chatter
                    body = Markup("El usuario <b>%s</b> eliminó las imágenes: %s") % (user_name, names)
                    rec.message_post(body=body)

        # 4) Auto-transición del flujo cuando se asigna/desasigna un técnico
        if 'portal_technician_id' in vals or 'user_id' in vals:
            for rec in self:
                has_tech = bool(rec.portal_technician_id or rec.user_id)
                if has_tech and rec.service_flow_state == 'to_assign':
                    rec.write({'service_flow_state': 'assigned'})
                elif not has_tech and rec.service_flow_state == 'assigned':
                    rec.write({'service_flow_state': 'to_assign'})

        return res



class ir_attachment(models.Model):
    _inherit = 'ir.attachment'

    car_repair_id = fields.Many2one('fleet.repair', 'Car Repair')


class ServiceType(models.Model):
    _name = 'service.type'
    _description = "Service Type"

    name = fields.Char(string='Name', required=True)

    _sql_constraints = [
        (
            'service_type_name_uniq',          # nombre interno del constraint
            'unique(name)',                   # regla SQL: el campo name debe ser único
            'Ya existe un tipo de servicio con este nombre.'  # mensaje de error
        ),
    ]


class FleetRepairLine(models.Model):
    _name = 'fleet.repair.line'
    _description = "Fleet repair line"

    fleet_id = fields.Many2one('fleet.vehicle', 'Car')
    license_plate = fields.Char('License Plate',
                                help='License plate number of the vehicle (ie: plate number for a car)')
    vin_sn = fields.Char('Chassis Number', help='Unique number written on the vehicle motor (VIN/SN number)')
    model_id = fields.Many2one('fleet.vehicle.model', 'Model', help='Model of the vehicle')
    vehicle_brand_id = fields.Many2one(
        'fleet.vehicle.model.brand',
        string='Marca',
        copy=False,
    )
    model_year = fields.Char(string='Modelo (año)', size=4, copy=False)
    engine_displacement = fields.Char(string='Cilindraje', size=8, copy=False)
    engine_number = fields.Char(string='Número de motor', size=64, copy=False)
    fuel_type = fields.Selection([('diesel', 'Diesel'),
                                  ('petrol', 'Petrol'),
                                  ('gasoline', 'Gasoline'),
                                  ('full_hybrid', 'Full Hybrid'),
                                  ('plug_in_hybrid_diesel', 'Plug-in Hybrid Diesel'),
                                  ('plug_in_hybrid_gasoline', 'Plug-in Hybrid Gasoline'),
                                  ('cng', 'CNG'),
                                  ('lpg', 'LPG'),
                                  ('hydrogen', 'Hydrogen'),
                                  ('electric', 'Electric'), ('hybrid', 'Hybrid')], 'Fuel Type',
                                 help='Fuel Used by the vehicle')
    guarantee = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Under Guarantee?')
    guarantee_type = fields.Selection(
        [('paid', 'paid'), ('free', 'Free')], string='Guarantee Type')
    service_type = fields.Many2one('service.type', string='Nature of Service')
    fleet_repair_id = fields.Many2one('fleet.repair', string='Car.', copy=False)
    service_detail = fields.Text(string='Service Details')
    diagnostic_result = fields.Text(string='Diagnostic Result')
    diagnose_id = fields.Many2one('fleet.diagnose', string='Car Diagnose', copy=False)
    workorder_id = fields.Many2one('fleet.workorder', string='Car Work Order', copy=False)
    source_line_id = fields.Many2one('fleet.repair.line', string='Source')
    tecnico_status = fields.Selection(
        [
            ('pendiente', 'Pendiente'),
            ('en_progreso', 'En progreso'),
            ('completado', 'Completado'),
        ],
        string="Estado del técnico",
        default='pendiente',
        tracking=True,
        help="Marca el avance del técnico sobre este servicio específico.",
    )
    tecnico_notes = fields.Text(
        string="Notas del técnico",
        help="Notas u observaciones del técnico al ejecutar este servicio.",
    )
    est_ser_hour = fields.Float(string='Estimated Sevice Hours')
    service_product_id = fields.Many2one('product.product', string='Service Product')
    service_product_price = fields.Float('Service Product Price')
    spare_part_ids = fields.One2many('spare.part.line', 'fleet_id', string='Spare Parts Needed')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('diagnosis', 'In Diagnosis'),
        ('done', 'Done'),
    ], 'Status', default="draft", readonly=True, copy=False, help="Gives the status of the fleet Diagnosis.",
        index=True)
    car_year = fields.Char(string="car Manufacturing Year")
    list_of_damage = fields.Char(string="Car Manufacturing Year")
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Almacén',
        help='Almacén desde el cual se reservarán los repuestos de esta orden.'
    )
    engine_number = fields.Char(
        string="Número de motor",
        related="fleet_id.engine_number",
        store=True,
        readonly=False,
    )

    _rec_name = 'fleet_id'

    @api.onchange('service_product_id')
    def onchange_service_product_id(self):
        for price in self:
            price.service_product_price = price.service_product_id.list_price

    def name_get(self):
        if not self._ids:
            return []
        if isinstance(self._ids, (int, int)):
            ids = [self._ids]
        reads = self.read(['fleet_id', 'license_plate'])
        res = []
        for record in reads:
            name = record['license_plate']
            if record['fleet_id']:
                name = record['fleet_id'][1]
            res.append((record['id'], name))
        return res

    def action_add_fleet_diagnosis_result(self):
        for obj in self:
            self.write({'state': 'done'})
        return True

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(FleetRepairLine, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        return res

    @api.onchange('fleet_id')
    def onchange_fleet_id(self):
        addr = {}
        if self.fleet_id:
            fleet = self.fleet_id
            addr['license_plate'] = fleet.license_plate
            addr['vin_sn'] = fleet.vin_sn
            addr['fuel_type'] = fleet.fuel_type
            addr['model_id'] = fleet.model_id.id
            addr['car_year'] = fleet.model_year
        return {'value': addr}


class FleetRepairAnalysis(models.Model):
    _name = 'fleet.repair.analysis'
    _description = "Fleet repair analysis"
    # _order = 'id desc'

    # id = fields.Integer('fleet Id', readonly=True)
    sequence = fields.Char(string='Sequence', readonly=True)
    receipt_date = fields.Date(string='Date of Receipt', readonly=True)
    state = fields.Selection([
        ('draft', 'Received'),
        ('diagnosis', 'In Diagnosis'),
        ('diagnosis_complete', 'Diagnosis Complete'),
        ('quote', 'Quotation Sent'),
        ('saleorder', 'Quotation Approved'),
        ('workorder', 'Work in Progress'),
        ('work_completed', 'Work Completed'),
        ('invoiced', 'Invoiced'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], 'Status', readonly=True, copy=False, help="Gives the status of the fleet repairing.", index=True)
    client_id = fields.Many2one('res.partner', string='Client', readonly=True)


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    repair_id = fields.Many2one('fleet.repair', string="Car Repair")
    diagnose_id = fields.Many2one('fleet.diagnose', string="Car diagnose")
    workorder_id = fields.Many2one('fleet.workorder', string="Car workorder")
    service_type = fields.Many2one('service.type', string="Service Type")

    @api.depends('service_type', 'unit_amount')
    def _cal_total_cost(self):
        for timesheet in self:
            if timesheet.type_id and (timesheet.unit_amount > 0):
                timesheet.total_cost = timesheet.service_type.cost * timesheet.unit_amount
            else:
                timesheet.total_cost = 0.0
