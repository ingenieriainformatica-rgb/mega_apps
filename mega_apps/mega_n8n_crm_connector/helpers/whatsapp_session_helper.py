# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime
from textwrap import dedent
from typing import Any
import random
from odoo import fields  # type: ignore
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
    COVERAGE_LOCATIONS,
    OUT_OF_COVERAGE_LOCATIONS,
    COLOMBIA_TZ,
)
from ..helpers.whatsapp_vehicle_helper import (
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
