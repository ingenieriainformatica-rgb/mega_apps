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
        ("advisor_handoff", "Pasado a asesor"),
        ("done", "Finalizado"),
    ], default="new", required=True, index=True)

    customer_name = fields.Char()
    vehicle_info = fields.Text()
    location = fields.Char()
    last_message = fields.Text()

    lead_id = fields.Many2one("crm.lead", string="Lead")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "phone_unique_active",
            "unique(phone, active)",
            "Ya existe una sesión activa para este teléfono.",
        )
    ]
