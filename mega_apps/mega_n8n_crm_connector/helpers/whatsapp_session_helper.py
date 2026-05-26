# -*- coding: utf-8 -*-

import json
import re
import logging
from datetime import datetime
from textwrap import dedent
from typing import Any
import random
from odoo import fields  # type: ignore
from markupsafe import Markup, escape

from .whatsapp_messages import (
    get_out_of_coverage_message,
    get_battery_selected_message,
)

from .constants import (
    CONFIRMATION_YES,
    CONFIRMATION_NO,
    ALLOWED_STEPS,
    MISSING_PHONE_REPLY,
    CONFIRMATION_RETRY_REPLY,
    RESET_SESSION_REPLY,
    TERMINAL_STEPS,
    SESSION_REOPEN_MINUTES,
    NEW_SESSION_KEYWORDS,
    WHATSAPP_LINE_CONFIGS,
    DEFAULT_WHATSAPP_LINE_CONFIG,
    COVERAGE_LOCATIONS,
    OUT_OF_COVERAGE_LOCATIONS,
    COLOMBIA_TZ,
)

from ..helpers.whatsapp_vehicle_helper import (
    build_vehicle_lead_values,
    build_vehicle_info_from_ai
)


_logger = logging.getLogger(__name__)


def normalize_text(value: str) -> str:
    value = (value or "").lower().strip()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value


def is_out_of_coverage(location: str) -> bool:
    normalized = normalize_text(location)

    if not normalized:
        return False

    allowed = [normalize_text(x) for x in COVERAGE_LOCATIONS]
    denied = [normalize_text(x) for x in OUT_OF_COVERAGE_LOCATIONS]

    if any(place in normalized for place in allowed):
        return False

    if any(place in normalized for place in denied):
        return True

    return False

def whatsapp_response(
    success: bool,
    step: str,
    reply: str = "",
    should_send: bool = True,
    **extra: Any,
) -> dict[str, Any]:
    response = {
        "success": success,
        "step": step,
        "should_send": should_send,
        "reply": reply,
    }
    response.update(extra)
    return response


def missing_phone_response(**extra: Any) -> dict[str, Any]:
    return whatsapp_response(
        False,
        "error",
        MISSING_PHONE_REPLY,
        should_send=True,
        **extra,
    )


def normalize_answer(message: str | None) -> str:
    return (message or "").strip().lower()


def get_session_model(env):
    return env["mega.whatsapp.session"].sudo()


def get_active_session(env, phone: str):
    return get_session_model(env).search(
        [
            ("phone", "=", phone),
            ("active", "=", True),
        ],
        limit=1,
    )


def create_session(env, phone: str, message: str, phone_number_id: str):
    return get_session_model(env).create(
        {
            "phone": phone,
            "phone_number_id": phone_number_id,
            "step": "ask_name",
            "last_message": message,
        }
    )


def write_last_message(session, message: str, phone_number_id: str) -> None:
    session.write(
        {
            "last_message": message,
            "phone_number_id": phone_number_id or session.phone_number_id,
        }
    )


def get_or_create_session(env, phone: str, message: str, phone_number_id: str):
    session = get_active_session(env, phone)

    _logger.info(
        "\n\nWHATSAPP SESSION CHECK phone=%s session=%s step=%s active=%s write_date=%s message=%s \n\n",
        phone,
        session.id if session else False,
        session.step if session else False,
        session.active if session else False,
        session.write_date if session else False,
        message,
    )

    if session and is_terminal_step(session.step):
        expired = terminal_session_expired(session)
        new_request = message_requests_new_session(message)

        _logger.info(
            "\n\n WHATSAPP TERMINAL SESSION phone=%s session=%s expired=%s new_request=%s \n\n",
            phone,
            session.id,
            expired,
            new_request,
        )

        if expired or new_request:
            _logger.info(
                "\n\nWHATSAPP CLOSING SESSION id=%s and creating new session\n\n",
                session.id,
            )
            close_session(session)
            new_session = create_session(env, phone, message, phone_number_id)

            _logger.info(
                "\n\nWHATSAPP NEW SESSION id=%s phone=%s step=%s\n\n",
                new_session.id,
                new_session.phone,
                new_session.step,
            )

            return new_session, True

    if session:
        write_last_message(session, message, phone_number_id)
        return session, False

    _logger.info("\n\nWHATSAPP CREATING FIRST SESSION phone=%s\n\n", phone)
    return create_session(env, phone, message, phone_number_id), True


def session_snapshot(session) -> dict[str, Any]:
    return {
        "id": session.id,
        "phone": session.phone,
        "customer_name": session.customer_name or "",
        "vehicle_info": session.vehicle_info or "",
        "location": session.location or "",
        "step": session.step,
    }


def get_colombia_greeting() -> str:
    hour = datetime.now(COLOMBIA_TZ).hour

    if 5 <= hour < 12:
        return "buenos días"

    if 12 <= hour < 19:
        return "buenas tardes"

    return "buenas noches"


def get_welcome_message() -> str:
    greeting = get_colombia_greeting()

    templates = [
        f"""
        🔋🚗 *MEGA BATERÍAS*

        Hola, muy {greeting}. 👋
        Un gusto saludarte.

        Te ayudamos a encontrar la batería adecuada para tu carro o camión, según tu vehículo y ubicación.

        • 📍 Cobertura: Medellín y área metropolitana
        • ⏰ Horario: 7am - 7pm (Lun a Sáb)
        • 🚗 Servicio para carros y camiones

        Para iniciar, ¿me regalas por favor tu nombre?
        """,

        f"""
        *BIENVENIDO A MEGA BATERÍAS* 🔋

        Muy {greeting}. 👋
        Gracias por comunicarte con nosotros.

        Cotizamos baterías para carros y camiones, validando la mejor opción según referencia, disponibilidad y ubicación.

        • 📍 Medellín y área metropolitana
        • ⏰ 7am - 7pm (Lun a Sáb)

        ¿Me compartes tu nombre para comenzar?
        """,

        f"""
        🚗🔋 *MEGA BATERÍAS*

        Muy {greeting}. Gracias por escribirnos.

        Estamos listos para asesorarte con la batería adecuada para tu vehículo.

        • 📍 Cobertura: Medellín y área metropolitana
        • ⏰ Horario: 7am - 7pm (Lun a Sáb)
        • 🚗 Carros y camiones

        ¿Cuál es tu nombre?
        """,
    ]

    return dedent(random.choice(templates)).strip()


def parse_ai_result(ai_result: Any) -> dict[str, Any]:
    if isinstance(ai_result, dict):
        return ai_result

    if isinstance(ai_result, str):
        try:
            parsed = json.loads(ai_result)
        except json.JSONDecodeError:
            _logger.warning("Invalid AI JSON result: %s", ai_result)
            return {}

        return parsed if isinstance(parsed, dict) else {}

    return {}

def build_ai_session_update(
    session,
    ai_result: dict[str, Any],
) -> tuple[str, bool, str, dict[str, Any]]:
    customer_name = (ai_result.get("customer_name") or "").strip()
    vehicle_info = build_vehicle_info_from_ai(
        ai_result,
        fallback=session.vehicle_info or "",
    )
    location = (ai_result.get("location") or "").strip()
    conversation_summary = (ai_result.get("conversation_summary") or "").strip()
    next_step = (ai_result.get("next_step") or session.step).strip()
    reply = (ai_result.get("reply") or "").strip()
    should_send = bool(ai_result.get("should_send", True))

    if next_step not in ALLOWED_STEPS:
        next_step = session.step

    current_name = customer_name or session.customer_name or ""
    current_vehicle = vehicle_info or session.vehicle_info or ""
    current_location = location or session.location or ""
    normalized_message = normalize_answer(session.last_message)

    if session.step == "catalog_sent":
        if any(word in normalized_message for word in [
            "opcion", "opción", "1", "2", "3",
            "economica", "económica", "barata",
            "mejor", "asesor"
        ]):
            return (
                "battery_selected",
                True,
                get_battery_selected_message(current_name),
                {
                    "step": "battery_selected",
                },
            )

        return (
            "catalog_sent",
            True,
            (
                "Para continuar, puedes responder con la opción que prefieres: "
                "opción 1, opción 2, la más económica, la mejor opción o quiero asesor. 🔋🚗"
            ),
            {
                "step": "catalog_sent",
            },
        )

    if current_location and is_out_of_coverage(current_location):
        next_step = "out_of_coverage"
        should_send = True
        reply = get_out_of_coverage_message()

        vals = build_session_vals(
            next_step,
            current_name,
            current_vehicle,
            current_location,
        )

        if conversation_summary and "conversation_summary" in session._fields:
            vals["conversation_summary"] = conversation_summary[:500]

        return next_step, should_send, reply, vals

    if session.step == "confirm_data":
        (
            next_step,
            should_send,
            reply,
            current_name,
            current_vehicle,
            current_location,
        ) = resolve_confirmation_from_ai(
            normalized_message,
            current_name,
            current_vehicle,
            current_location,
        )

        if next_step == "catalog_sent":
            reply = (
                f"Perfecto {current_name} 👍\n\n"
                f"Ya validamos los datos de tu vehículo: {current_vehicle}.\n\n"
                "En este momento estamos consultando las baterías compatibles "
                "para enviarte las mejores opciones disponibles. 🔋🚗"
            )
            should_send = True

    elif not current_name:
        next_step = "ask_name"
        should_send = True
        reply = reply or "Con gusto te ayudo. ¿Me regalas por favor tu nombre?"

    elif not current_vehicle:
        next_step = "ask_vehicle"
        should_send = True
        reply = reply or f"Gracias {current_name}. ¿Para qué vehículo necesitas la batería? 🔋🚗"

    elif not current_location:
        next_step = "ask_location"
        should_send = True
        reply = reply or (
            f"Perfecto {current_name}. ¿En qué barrio o ubicación te encuentras "
            "para validar cobertura y disponibilidad?"
        )

    elif next_step not in {"confirm_data", "catalog_sent", "advisor_handoff"}:
        next_step = "confirm_data"
        should_send = True


    vals = build_session_vals(
        next_step,
        current_name,
        current_vehicle,
        current_location,
    )

    if conversation_summary and "conversation_summary" in session._fields:
        vals["conversation_summary"] = conversation_summary[:500]

    return next_step, should_send, reply, vals


def resolve_confirmation_from_ai(
    normalized_message: str,
    current_name: str,
    current_vehicle: str,
    current_location: str,
) -> tuple[str, bool, str, str, str, str]:

    if normalized_message in CONFIRMATION_YES:
        # return (
        #     "advisor_handoff",
        #     True,
        #     advisor_handoff_reply(current_name),
        #     current_name,
        #     current_vehicle,
        #     current_location,
        # )
        return (
            "catalog_sent",
            True,
            "",
            current_name,
            current_vehicle,
            current_location,
        )

    if normalized_message in CONFIRMATION_NO:
        return (
            "ask_name",
            True,
            RESET_SESSION_REPLY,
            "",
            "",
            "",
        )

    return (
        "confirm_data",
        True,
        CONFIRMATION_RETRY_REPLY,
        current_name,
        current_vehicle,
        current_location,
    )


def build_session_vals(
    next_step: str,
    current_name: str,
    current_vehicle: str,
    current_location: str,
) -> dict[str, Any]:
    vals: dict[str, Any] = {
        "step": next_step,
    }

    if current_name:
        vals["customer_name"] = current_name

    if current_vehicle:
        vals["vehicle_info"] = current_vehicle

    if current_location:
        vals["location"] = current_location

    if next_step == "ask_name":
        vals.update(
            {
                "customer_name": False,
                "vehicle_info": False,
                "location": False,
            }
        )

    return vals


def is_terminal_step(step: str | None) -> bool:
    return step in TERMINAL_STEPS


def message_requests_new_session(message: str | None) -> bool:
    normalized = normalize_answer(message)

    return any(keyword in normalized for keyword in NEW_SESSION_KEYWORDS)


def terminal_session_expired(session) -> bool:
    if not is_terminal_step(session.step):
        return False

    if not session.write_date:
        return False

    expiration_limit = fields.Datetime.subtract(
        fields.Datetime.now(),
        minutes=SESSION_REOPEN_MINUTES,
    )

    return session.write_date < expiration_limit


def close_session(session) -> None:
    session.write(
        {
            "active": False,
            "step": "done",
        }
    )

    session.flush_recordset(["active", "step"])


############### CREACIÓN DE CRM ###############
###############################################

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

def post_whatsapp_note_on_lead(lead, title: str, message: str | None) -> None:
    if not lead or not message:
        return

    safe_title = escape(title)
    safe_message = escape(message).replace("\n", Markup("<br/>"))

    body = Markup(
        """
        <div>
            <p><strong>%s</strong></p>
            <p>%s</p>
        </div>
        """
    ) % (safe_title, safe_message)

    lead.message_post(
        body=body,
        subtype_xmlid="mail.mt_note",
    )

def log_whatsapp_conversation_on_lead(
    lead,
    customer_message: str | None,
    bot_reply: str | None,
) -> None:
    if not lead:
        return

    parts = []

    if customer_message:
        parts.append(
            Markup("<p><strong>Cliente por WhatsApp:</strong><br/>%s</p>")
            % escape(customer_message).replace("\n", Markup("<br/>"))
        )

    if bot_reply:
        parts.append(
            Markup("<p><strong>Respuesta automática:</strong><br/>%s</p>")
            % escape(bot_reply).replace("\n", Markup("<br/>"))
        )

    if not parts:
        return

    body = Markup("<div>%s</div>") % Markup("").join(parts)

    lead.message_post(
        body=body,
        subtype_xmlid="mail.mt_note",
    )


def get_crm_team_by_name(env, name: str):
    return env["crm.team"].sudo().search(
        [("name", "=", name)],
        limit=1,
    )


def get_user_by_name(env, name: str):
    return env["res.users"].sudo().search(
        [("name", "=", name)],
        limit=1,
    )


def get_whatsapp_line_label(phone_number_id: str | None) -> str:
    config = get_whatsapp_line_config(phone_number_id)
    return config.get("label", "Mega Baterías")


def get_default_lead_website(session) -> str:
    config = get_whatsapp_line_config(session.phone_number_id)
    return config.get("website", "https://megabaterias.co")


def get_default_team_name(session) -> str:
    config = get_whatsapp_line_config(session.phone_number_id)
    return config.get("team_name", "Baterías")


def get_default_user_name(session) -> str:
    config = get_whatsapp_line_config(session.phone_number_id)
    return config.get("user_name", "TIENDA DIGITAL")


def get_whatsapp_line_config(phone_number_id: str | None) -> dict:
    phone_number_id = (phone_number_id or "").strip()

    return WHATSAPP_LINE_CONFIGS.get(
        phone_number_id,
        DEFAULT_WHATSAPP_LINE_CONFIG,
    )

def log_customer_message_on_lead_from_session(
    session,
    message: str | None,
    message_id: str | None = None,
) -> bool:
    message = (message or "").strip()
    message_id = (message_id or "").strip()

    if not message:
        return False

    if not session or not session.lead_id:
        return False

    if (
        message_id
        and "last_inbound_message_id" in session._fields
        and session.last_inbound_message_id == message_id
    ):
        return False

    post_whatsapp_message_on_lead(
        session.lead_id,
        "Cliente por WhatsApp",
        message,
    )

    values = {
        "last_message": message,
    }

    if message_id and "last_inbound_message_id" in session._fields:
        values["last_inbound_message_id"] = message_id

    session.write(values)

    return True


def post_whatsapp_message_on_lead(lead, title: str, message: str | None) -> None:
    if not lead or not message:
        return

    safe_title = escape(title)
    safe_message = escape(message).replace("\n", Markup("<br/>"))

    body = Markup(
        """
        <div>
            <p><strong>%s</strong></p>
            <p>%s</p>
        </div>
        """
    ) % (safe_title, safe_message)

    lead.message_post(
        body=body,
        subtype_xmlid="mail.mt_note",
    )
