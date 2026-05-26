from odoo import fields  # type: ignore

from .constants import (
    WHATSAPP_LINE_CONFIGS,
    DEFAULT_WHATSAPP_LINE_CONFIG,
)

from .whatsapp_vehicle_helper import (
    build_vehicle_lead_values,
    build_vehicle_info_from_ai
)

def get_partner_model(env):
    return env["res.partner"].sudo()

def get_lead_model(env):
    return env["crm.lead"].sudo()

def normalize_phone(phone: str | None) -> str:
    return "".join(char for char in (phone or "") if char.isdigit())

def find_partner_by_phone(env, phone: str):
    phone_normalized = normalize_phone(phone)

    if not phone_normalized:
        return False

    Partner = get_partner_model(env)

    partner = Partner.search(
        [
            "|",
            ("mobile", "=", phone_normalized),
            ("phone", "=", phone_normalized),
        ],
        limit=1,
    )

    if partner:
        return partner

    last_digits = phone_normalized[-10:] if len(phone_normalized) >= 10 else phone_normalized

    if last_digits:
        return Partner.search(
            [
                "|",
                ("mobile", "ilike", last_digits),
                ("phone", "ilike", last_digits),
            ],
            limit=1,
        )

    return False

def get_or_create_partner_from_session(env, session):
    customer_name = (session.customer_name or "").strip()
    phone = normalize_phone(session.phone)

    if not customer_name or not phone:
        return False

    partner = find_partner_by_phone(env, phone)

    if partner:
        values = {}

        if not partner.mobile:
            values["mobile"] = phone

        if not partner.phone:
            values["phone"] = phone

        # Solo actualizamos el nombre si parece genérico.
        if partner.name and partner.name.lower().startswith("whatsapp"):
            values["name"] = customer_name

        if values:
            partner.write(values)

        return partner

    return get_partner_model(env).create(
        {
            "name": customer_name,
            "phone": phone,
            "mobile": phone,
            "customer_rank": 1,
        }
    )

def build_lead_description_from_session(session) -> str:
    line_label = get_whatsapp_line_label(session.phone_number_id)

    return "\n".join(
        [
            "Lead creado desde WhatsApp vía n8n.",
            "",
            f"Línea WhatsApp: {line_label}",
            f"Phone Number ID: {session.phone_number_id or 'No registrado'}",
            f"Teléfono cliente: {session.phone or 'No registrado'}",
            f"Nombre: {session.customer_name or 'No registrado'}",
            f"Vehículo: {session.vehicle_info or 'No registrado'}",
            f"Ubicación: {session.location or 'No registrada'}",
        ]
    )


def get_whatsapp_line_label(phone_number_id: str | None) -> str:
    config = get_whatsapp_line_config(phone_number_id)
    return config.get("label", "Mega Baterías")


def get_whatsapp_line_config(phone_number_id: str | None) -> dict:
    phone_number_id = (phone_number_id or "").strip()

    return WHATSAPP_LINE_CONFIGS.get(
        phone_number_id,
        DEFAULT_WHATSAPP_LINE_CONFIG,
    )


def create_or_update_lead_from_session(env, session, ai_result=None):
    """
    Crea o actualiza el lead CRM asociado a la sesión.

    Reglas:
    - No crea lead si todavía no hay nombre.
    - Si no existe contacto, lo crea.
    - Si no existe lead en la sesión, lo crea.
    - Si ya existe lead_id, actualiza datos variables pero NO cambia el título.
    - crm_fecha_instalacion solo se asigna al crear el lead.
    - team_id, user_id y website solo se asignan al crear el lead.
    """
    ai_result = ai_result or {}
    customer_name = (session.customer_name or "").strip()

    if not customer_name:
        return False

    partner = get_or_create_partner_from_session(env, session)

    if not partner:
        return False

    phone = normalize_phone(session.phone)
    line_label = get_whatsapp_line_label(session.phone_number_id)
    Lead = get_lead_model(env)

    common_values = {
        "partner_id": partner.id,
        "contact_name": customer_name,
        "phone": phone or session.phone or partner.phone or partner.mobile,
        "description": build_lead_description_from_session(session),
        "type": "opportunity",
    }

    vehicle_values = build_vehicle_lead_values(env, Lead, ai_result)
    common_values.update(vehicle_values)

    # Si ya existe lead, solo actualizamos datos variables.
    # No tocamos:
    # - name
    # - crm_fecha_instalacion
    # - team_id
    # - user_id
    # - website
    if session.lead_id:
        session.lead_id.write(common_values)
        return session.lead_id

    # Si no existe lead, ahí sí definimos valores iniciales.
    lead_values = {
        **common_values,
        "name": f"{line_label} - WhatsApp - {customer_name}",
    }

    # Fecha de instalación / creación del servicio.
    # Solo se asigna una vez al crear el lead.
    if "crm_fecha_instalacion" in Lead._fields:
        lead_values["crm_fecha_instalacion"] = fields.Datetime.now()

    # Equipo de ventas según la línea de WhatsApp.
    if "team_id" in Lead._fields:
        team = get_crm_team_by_name(
            env,
            get_default_team_name(session),
        )
        if team:
            lead_values["team_id"] = team.id

    # Vendedor según la línea de WhatsApp.
    if "user_id" in Lead._fields:
        user = get_user_by_name(
            env,
            get_default_user_name(session),
        )
        if user:
            lead_values["user_id"] = user.id

    # Website según la línea de WhatsApp.
    if "website" in Lead._fields:
        lead_values["website"] = get_default_lead_website(session)

    lead = Lead.create(lead_values)

    session.write(
        {
            "lead_id": lead.id,
        }
    )

    return lead


def get_crm_team_by_name(env, name: str):
    return env["crm.team"].sudo().search(
        [("name", "=", name)],
        limit=1,
    )


def get_default_team_name(session) -> str:
    config = get_whatsapp_line_config(session.phone_number_id)
    return config.get("team_name", "Baterías")


def get_user_by_name(env, name: str):
    return env["res.users"].sudo().search(
        [("name", "=", name)],
        limit=1,
    )


def get_default_user_name(session) -> str:
    config = get_whatsapp_line_config(session.phone_number_id)
    return config.get("user_name", "TIENDA DIGITAL")


def get_default_lead_website(session) -> str:
    config = get_whatsapp_line_config(session.phone_number_id)
    return config.get("website", "https://megabaterias.co")
