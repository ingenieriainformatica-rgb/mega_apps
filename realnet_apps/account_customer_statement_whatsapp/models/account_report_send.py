from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.addons.whatsapp.tools import phone_validation as wa_phone_validation
from odoo.addons.whatsapp.tools.whatsapp_exception import WhatsAppError

class AccountReportSend(models.TransientModel):
    _inherit = "account.report.send"

    delivery_channel = fields.Selection(
        selection=[('email', 'Email'), ('whatsapp', 'WhatsApp')],
        default='email', required=True, string="Canal de envío"
    )
    whatsapp_template_id = fields.Many2one(
        "whatsapp.template", string="Plantilla de WhatsApp",
        domain=[('status', '=', 'approved'), ('model', '=', 'res.partner')],  # estado aprobado en Meta
        help="Plantilla con Header = Document para adjuntar el PDF del estado."
    )

    # Campos visuales para la sección WhatsApp
    whatsapp_phone = fields.Char(string="Número detectado", compute='_compute_whatsapp_info')
    whatsapp_preview = fields.Html(string="Vista previa WhatsApp", compute='_compute_whatsapp_info')
    whatsapp_attachments_widget = fields.Json(compute='_compute_whatsapp_attachments_widget', store=True, readonly=False)

    @api.depends('partner_ids', 'whatsapp_template_id', 'delivery_channel')
    def _compute_whatsapp_info(self):
        for wizard in self:
            phone_display = False
            preview_html = False
            if wizard.delivery_channel == 'whatsapp' and wizard.mode == 'single' and wizard.partner_ids:
                partner = wizard.partner_ids[0]
                # Detectar número utilizando la misma lógica de WhatsApp
                phone_field = False
                template = wizard.whatsapp_template_id
                if not template:
                    template = wizard.env['whatsapp.template']._find_default_for_model('res.partner')
                if template:
                    phone_field = template.phone_field
                raw_number = False
                if phone_field and hasattr(partner, phone_field):
                    raw_number = getattr(partner, phone_field)
                else:
                    raw_number = partner.mobile or partner.phone
                try:
                    phone_display = wa_phone_validation.wa_phone_format(partner, number=raw_number, force_format="WHATSAPP", raise_exception=False)
                except Exception:
                    phone_display = raw_number

                # Vista previa básica usando el cuerpo de la plantilla con demo_fallback
                if template:
                    try:
                        preview_html = template._get_formatted_body(demo_fallback=True)
                    except Exception:
                        preview_html = False

            wizard.whatsapp_phone = phone_display or ''
            wizard.whatsapp_preview = preview_html or ''

    def _generate_statement_attachment(self, partner):
        """Usa la acción de reporte del Estado del cliente para 'partner'.
        Crea y devuelve un ir.attachment listo para adjuntar al WhatsApp.
        """
        self.ensure_one()
        # Intentar usar la API nativa de account_reports para generar el adjunto
        if self.account_report_id:
            options = dict(self.report_options or {})
            options.update({'partner_ids': [partner.id], 'unfold_all': True})
            attachment_alt = partner._get_partner_account_report_attachment(self.account_report_id, options)
            if attachment_alt:
                return attachment_alt[0] if hasattr(attachment_alt, '__getitem__') else attachment_alt
        # 1) localizar la acción de reporte que ya usa el asistente estándar
        report_action = self.env.ref("account_reports.action_account_report_customer_statement")  # localizar en tu BD (dev mode)
        # 2) renderizar PDF (QWeb) y crear attachment
        pdf, _ = report_action._render_qweb_pdf([partner.id])  # QWeb render del PDF
        filename = f"Estado_de_cuenta_{partner.display_name}.pdf"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'mimetype': 'application/pdf',
            'raw': pdf,
            'res_model': 'res.partner',
            'res_id': partner.id,
        })
        return attachment

    def _open_whatsapp_composer(self, partner, attachment):
        """Abre el composer nativo de WhatsApp con plantilla, partner y documento."""
        self.ensure_one()
        # No exigimos plantilla aquí; el wizard de WhatsApp buscará una por defecto.
        if not (partner.mobile or partner.phone):
            raise UserError(f"El contacto {partner.display_name} no tiene teléfono móvil/fijo.")

        # Abrimos el popup estándar del compositor de WhatsApp con contexto por defecto:
        return {
            "type": "ir.actions.act_window",
            "res_model": "whatsapp.composer",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_model": "res.partner",
                "active_ids": [partner.id],
                "default_wa_template_id": (self.whatsapp_template_id.id if self.whatsapp_template_id else False),
                # Sugerencia: si tu plantilla usa Header=Document, el propio wizard
                # tomará 'document' desde el context/adjuntos; pasamos el attachment:
                "default_attachment_id": attachment.id,
            },
        }

    def action_send(self):
        self.ensure_one()
        if self.delivery_channel != 'whatsapp':
            # Flujo original (Email)
            return super().action_send()

        actions = []
        for partner in self.partner_ids:
            att = self._generate_statement_attachment(partner)
            actions.append(self._open_whatsapp_composer(partner, att))
        # Si es 1 contacto, devolvemos directamente el popup; si son varios,
        # puedes devolver una acción "multi" o secuenciar popups (a elección UX)
        return actions[0] if len(actions) == 1 else actions

    # Botones de cambio de canal (para la UI)
    def _reopen_self(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.report.send',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_switch_to_email(self):
        self.ensure_one()
        self.delivery_channel = 'email'
        self.checkbox_send_mail = True
        return self._reopen_self()

    def action_switch_to_whatsapp(self):
        self.ensure_one()
        self.delivery_channel = 'whatsapp'
        # Ocultar el composer de email cuando se usa WhatsApp
        self.checkbox_send_mail = False
        # Seleccionar plantilla por defecto si no hay una elegida
        if not self.whatsapp_template_id:
            default_template = self.env['whatsapp.template']._find_default_for_model('res.partner')
            if default_template:
                self.whatsapp_template_id = default_template
        # Forzar que el botón 'Imprimir y enviar' esté visible
        self.checkbox_download = True
        return self._reopen_self()

    # Botón principal de la vista (Imprimir y enviar)
    def action_send_and_print(self, force_synchronous=False):
        self.ensure_one()
        if self.delivery_channel == 'whatsapp':
            # Enviar directamente por WhatsApp sin abrir compositor
            return self._action_send_whatsapp_direct()
        return super().action_send_and_print(force_synchronous=force_synchronous)

    def _action_send_whatsapp_direct(self):
        self.ensure_one()
        # Seleccionar plantilla: elegida en el wizard o la aprobada por defecto
        template = self.whatsapp_template_id or self.env['whatsapp.template']._find_default_for_model('res.partner')
        if not template:
            raise UserError('No hay plantillas de WhatsApp aprobadas para Contactos.')

        successes = 0
        errors = []
        for partner in self.partner_ids:
            try:
                # Generar el PDF del estado de cuenta para este partner
                attachment = self._generate_statement_attachment(partner)
                # Crear el wizard internamente para reutilizar la lógica de envío
                composer = self.env['whatsapp.composer'].with_context(
                    active_model='res.partner',
                    active_ids=[partner.id],
                ).sudo().create({
                    'res_model': 'res.partner',
                    'res_ids': str([partner.id]),
                    'wa_template_id': template.id,
                    'attachment_id': attachment.id,
                })
                # Validaciones de número y variables se manejan dentro del wizard
                composer._send_whatsapp_template(force_send_by_cron=False)
                successes += 1
            except (ValidationError, UserError, WhatsAppError) as e:
                errors.append(f"{partner.display_name}: {str(e)}")

        # Preparar notificación al usuario
        if errors:
            # Mostrar hasta 5 errores para no saturar la notificación
            sample = '\n'.join(errors[:5])
            message = f"Envío de WhatsApp: {successes} enviados, {len(errors)} con error.\n{sample}"
            notif_type = 'warning' if successes else 'danger'
        else:
            message = 'Mensaje(s) de WhatsApp enviados correctamente.'
            notif_type = 'success'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': notif_type,
                'title': 'Enviar por WhatsApp',
                'message': message,
                'next': {'type': 'ir.actions.act_window_close'},
                'sticky': False,
            },
        }

    # ------------------------------------------------------------
    # WhatsApp attachments placeholder (preview)
    # ------------------------------------------------------------
    @api.depends('delivery_channel', 'mode', 'partner_ids', 'report_options', 'account_report_id')
    def _compute_whatsapp_attachments_widget(self):
        for wizard in self:
            if wizard.delivery_channel == 'whatsapp' and wizard.mode == 'single' and wizard.partner_ids:
                try:
                    wizard.whatsapp_attachments_widget = wizard._get_placeholder_mail_attachments_data(wizard.partner_ids[0])
                except Exception:
                    wizard.whatsapp_attachments_widget = []
            else:
                wizard.whatsapp_attachments_widget = []
