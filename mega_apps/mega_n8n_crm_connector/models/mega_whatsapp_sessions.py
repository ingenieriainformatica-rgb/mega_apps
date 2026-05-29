from odoo import models, api, fields  #type: ignore


class MegaWhatsappSession(models.Model):
    _name = "mega.whatsapp.session"
    _description = "Sesión WhatsApp n8n"
    _order = "write_date desc"

    phone = fields.Char(required=True, index=True)
    phone_number_id = fields.Char(index=True)

    step = fields.Selection([
        ("new", "Nuevo"),
        ("ask_name", "Preguntar nombre"),
        ("ask_vehicle", "Preguntar vehículo"),
        ("ask_location", "Preguntar ubicación"),
        ("confirm_data", "Confirmar datos"),
        ("out_of_coverage", "Fuera de cobertura"),

        ("catalog_sent", "Opción recomendada enviada"),
        ("more_options_sent", "Más opciones enviadas"),
        ("more_catalog_sent", "Catálogo adicional enviado"),
        ("battery_selected", "Batería seleccionada"),
        ("dispatch_requested", "Despacho solicitado"),

        ("payment_link_sent", "Link de pago enviado"),

        ("advisor_handoff", "Pasado a asesor"),
        ("done", "Finalizado"),
    ], default="new", required=True, index=True)

    customer_name = fields.Char()
    vehicle_info = fields.Text()
    location = fields.Char()
    last_message = fields.Text()

    lead_id = fields.Many2one("crm.lead", string="Lead")
    active = fields.Boolean(default=True)

    last_inbound_message_id = fields.Char(index=True)

    conversation_summary = fields.Text(
        string="Resumen conversación IA",
        help="Resumen corto del contexto conversacional enviado al modelo IA.",
    )

    selected_battery_option_id = fields.Many2one(
        "mega.battery.application.option",
        string="Batería seleccionada",
    )

    customer_leaves_old_battery = fields.Boolean(
        string="Cliente entrega batería usada",
        default=True,
    )

    selected_battery_price = fields.Float(
        string="Precio batería seleccionado",
    )

    wompi_payment_link_id = fields.Char(
        string="ID link Wompi",
        readonly=True,
    )

    wompi_payment_url = fields.Char(
        string="URL de pago Wompi",
        readonly=True,
    )

    def init(self):
        self.env.cr.execute("""
            ALTER TABLE mega_whatsapp_session
            DROP CONSTRAINT IF EXISTS mega_whatsapp_session_phone_unique_active
        """)

        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS mega_whatsapp_session_unique_active_phone_idx
            ON mega_whatsapp_session (phone)
            WHERE active IS TRUE
        """)
