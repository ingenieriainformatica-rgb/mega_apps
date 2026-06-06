from odoo import models, api, fields  #type: ignore


class MegaWhatsappSession(models.Model):
    _name = "mega.whatsapp.session"
    _description = "Sesión WhatsApp n8n"
    _order = "write_date desc"

    phone = fields.Char(required=True, index=True)
    phone_number_id = fields.Char(index=True)
    welcome_sent = fields.Boolean(
        string="Bienvenida enviada",
        default=False,
        help="Indica si ya se envió el mensaje completo de bienvenida al cliente.",
    )

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
        ("after_hours_handoff", "Fuera de horario - datos tomados"),
        ("done", "Finalizado"),
    ], default="new", required=True, index=True)

    customer_name = fields.Char()
    vehicle_brand = fields.Char()
    vehicle_model = fields.Char()
    vehicle_year = fields.Char()
    vehicle_type = fields.Char()
    vehicle_info = fields.Text()
    city = fields.Char()
    neighborhood = fields.Char()
    location = fields.Char()
    coverage_status = fields.Selection(
        [
            ("covered", "Cubierta"),
            ("out_of_coverage", "Fuera de cobertura"),
            ("ambiguous", "Ambigua"),
            ("not_provided", "No proporcionada"),
        ],
        default="not_provided",
        index=True,
    )
    plate = fields.Char()
    battery_request = fields.Boolean(default=False)
    relevant_data = fields.Text()
    last_message = fields.Text()
    is_after_hours = fields.Boolean(
        string="Fuera de horario",
        default=False,
    )
    after_hours_accepted = fields.Boolean(
        string="Aceptó dejar datos fuera de horario",
        default=False,
    )

    lead_id = fields.Many2one("crm.lead", string="Lead")
    discuss_channel_id = fields.Many2one(
        "discuss.channel",
        string="Conversación Discuss",
        readonly=True,
        copy=False,
        help="Canal de Discuss/WhatsApp creado cuando la sesión pasa a atención humana.",
    )
    discuss_summary_posted = fields.Boolean(
        string="Resumen publicado en Discuss",
        default=False,
        copy=False,
    )
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

    last_catalog_option_ids = fields.Char(
        string="Últimas opciones mostradas",
        help="IDs de las últimas opciones de batería mostradas al cliente, separados por coma.",
    )

    last_catalog_type = fields.Selection([
        ("recommended", "Recomendada"),
        ("more_options", "Más opciones"),
    ], default=False)

    last_catalog_sent_at = fields.Datetime(
        string="Último catálogo enviado",
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
