import logging

from odoo import fields  # type: ignore

from .constants import (
    WHATSAPP_LINE_CONFIGS,
    DEFAULT_WHATSAPP_LINE_CONFIG,
)
from .whatsapp_business_hours_helper import get_business_hours_text
from .whatsapp_session_helper import is_out_of_coverage

from .whatsapp_vehicle_helper import (
    build_vehicle_lead_values,
    build_vehicle_info_from_ai
)

_logger = logging.getLogger(__name__)


def get_provisional_contact_label(session) -> str:
    phone = (session.phone or "").strip()
    return f"WhatsApp {phone}" if phone else "WhatsApp"


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

    if not phone:
        return False

    partner = find_partner_by_phone(env, phone)

    if partner:
        values = {}

        if not partner.mobile:
            values["mobile"] = phone

        if not partner.phone:
            values["phone"] = phone

        # Solo actualizamos el nombre si parece genérico/provisional y ya
        # tenemos un nombre real que reemplazarlo.
        if customer_name and partner.name and partner.name.lower().startswith("whatsapp"):
            values["name"] = customer_name
            _logger.info(
                "[WHATSAPP CRM] Updating provisional partner name partner=%s phone=%s name=%s",
                partner.id,
                phone,
                customer_name,
            )

        if values:
            partner.write(values)

        return partner

    is_provisional = not customer_name
    partner = get_partner_model(env).create(
        {
            "name": customer_name or get_provisional_contact_label(session),
            "phone": phone,
            "mobile": phone,
            "customer_rank": 1,
        }
    )

    if is_provisional:
        _logger.info(
            "[WHATSAPP CRM] Created provisional partner id=%s phone=%s",
            partner.id,
            phone,
        )

    return partner

def build_lead_description_from_session(session) -> str:
    line_label = get_whatsapp_line_label(session.phone_number_id)
    after_hours_lines = []

    if bool(getattr(session, "is_after_hours", False)):
        after_hours_lines = [
            "",
            "Lead fuera de horario: Sí",
            "Lead urgente: Sí",
            f"Horario de atención: {get_business_hours_text()}",
        ]

    return "\n".join(
        [
            "Lead creado desde WhatsApp vía n8n.",
            "",
            f"Línea WhatsApp: {line_label}",
            f"Phone Number ID: {session.phone_number_id or 'No registrado'}",
            f"Teléfono cliente: {session.phone or 'No registrado'}",
            f"Nombre: {session.customer_name or 'No registrado'}",
            f"Vehículo: {session.vehicle_info or 'No registrado'}",
            f"Marca: {getattr(session, 'vehicle_brand', '') or 'No registrada'}",
            f"Modelo/Línea: {getattr(session, 'vehicle_model', '') or 'No registrado'}",
            f"Año: {getattr(session, 'vehicle_year', '') or 'No registrado'}",
            f"Tipo de vehículo: {getattr(session, 'vehicle_type', '') or 'No registrado'}",
            f"Ciudad: {getattr(session, 'city', '') or 'No registrada'}",
            f"Barrio: {getattr(session, 'neighborhood', '') or 'No registrado'}",
            f"Ubicación: {session.location or 'No registrada'}",
            f"Placa: {getattr(session, 'plate', '') or 'No registrada'}",
            f"Solicitud de batería: {'Sí' if getattr(session, 'battery_request', False) else 'No'}",
            f"Datos relevantes: {getattr(session, 'relevant_data', '') or 'No registrados'}",
        ]
        + after_hours_lines
    )


def session_has_qualified_lead_data(session) -> bool:
    has_name = bool((session.customer_name or "").strip())
    location = (session.location or "").strip()
    has_location = bool(location)
    has_vehicle = bool(
        (getattr(session, "vehicle_brand", "") or "").strip()
        and (getattr(session, "vehicle_model", "") or "").strip()
        and (getattr(session, "vehicle_year", "") or "").strip()
    )
    has_valid_location = has_location and not is_out_of_coverage(location)

    return has_name and has_valid_location and has_vehicle


def apply_qualified_lead_priority(Lead, lead_values: dict, session) -> dict:
    if session_has_qualified_lead_data(session) and "priority" in Lead._fields:
        lead_values["priority"] = "3"

    return lead_values


def apply_default_team_values(env, Lead, lead_values: dict, session) -> dict:
    if "team_id" not in Lead._fields:
        return lead_values

    team = get_crm_team_by_name(
        env,
        get_default_team_name(session),
    )

    if team:
        lead_values["team_id"] = team.id

    return lead_values


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
    - Crea lead/partner provisional desde el primer contacto, aunque todavía
      no haya nombre (usa el teléfono como identidad provisional).
    - Si no existe contacto, lo crea.
    - Si no existe lead en la sesión, lo crea.
    - Si ya existe lead_id, actualiza datos variables.
    - El título (name) del lead solo cambia una vez: en la transición de
      provisional a nombre real. Fuera de esa transición, no se toca.
    - crm_fecha_instalacion solo se asigna al crear el lead.
    - team_id se mantiene según la línea de WhatsApp para evitar que reglas externas lo muevan.
    - user_id y website solo se asignan al crear el lead.
    """
    ai_result = ai_result or {}
    customer_name = (session.customer_name or "").strip()

    partner = get_or_create_partner_from_session(env, session)

    if not partner:
        return False

    phone = normalize_phone(session.phone)
    line_label = get_whatsapp_line_label(session.phone_number_id)
    display_name = customer_name or phone
    Lead = get_lead_model(env)

    common_values = {
        "partner_id": partner.id,
        "contact_name": display_name,
        "phone": phone or session.phone or partner.phone or partner.mobile,
        "description": build_lead_description_from_session(session),
        "type": "opportunity",
    }

    vehicle_values = build_vehicle_lead_values(env, Lead, ai_result)
    common_values.update(vehicle_values)
    apply_qualified_lead_priority(Lead, common_values, session)
    apply_default_team_values(env, Lead, common_values, session)

    # Si ya existe lead, solo actualizamos datos variables.
    # El título (name) no se toca, salvo la transición provisional -> nombre real.
    if session.lead_id:
        existing_lead = session.lead_id
        had_provisional_name = (existing_lead.contact_name or "").strip() == phone

        if had_provisional_name and customer_name:
            common_values["name"] = f"{line_label} - WhatsApp - {customer_name}"
            _logger.info(
                "[WHATSAPP CRM] Updating provisional lead title with real name lead=%s customer_name=%s",
                existing_lead.id,
                customer_name,
            )

        existing_lead.write(common_values)
        return existing_lead

    # Si no existe lead, ahí sí definimos valores iniciales (puede ser provisional).
    lead_values = {
        **common_values,
        "name": f"{line_label} - WhatsApp - {display_name}",
    }
    apply_qualified_lead_priority(Lead, lead_values, session)

    # Fecha de instalación / creación del servicio.
    # Solo se asigna una vez al crear el lead.
    if "crm_fecha_instalacion" in Lead._fields:
        lead_values["crm_fecha_instalacion"] = fields.Datetime.now()

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

    if customer_name:
        _logger.info(
            "[WHATSAPP CRM] Created lead id=%s phone=%s customer_name=%s",
            lead.id,
            phone,
            customer_name,
        )
    else:
        _logger.info(
            "[WHATSAPP CRM] Created provisional lead id=%s phone=%s phone_number_id=%s",
            lead.id,
            phone,
            session.phone_number_id,
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
