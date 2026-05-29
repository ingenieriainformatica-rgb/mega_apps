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

def parse_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = normalize_text(value)
        if normalized in {"false", "0", "no", "n"}:
            return False
        if normalized in {"true", "1", "si", "s", "yes", "y"}:
            return True

    if value is None:
        return default

    return bool(value)

def message_confirms_data(normalized_message: str, intent: str = "") -> bool:
    if intent == "confirm_data_correct":
        return True

    if normalized_message in CONFIRMATION_YES:
        return True

    confirmation_phrases = {
        "todo bien",
        "todo esta bien",
        "todo está bien",
        "esta bien",
        "está bien",
        "asi esta bien",
        "así está bien",
        "asi esta perfecto",
        "así está perfecto",
        "esta perfecto",
        "está perfecto",
        "perfecto",
        "de una",
        "dale",
        "avancemos",
        "continua",
        "continúa",
        "sigue",
        "sigamos",
        "correcto todo",
        "los datos estan bien",
        "los datos están bien",
    }

    return any(phrase in normalized_message for phrase in confirmation_phrases)

def message_requests_data_correction(normalized_message: str, intent: str = "") -> bool:
    if intent == "correct_data":
        return True

    if normalized_message in CONFIRMATION_NO:
        return True

    correction_phrases = {
        "no esta bien",
        "no está bien",
        "no es correcto",
        "esta mal",
        "está mal",
        "hay que corregir",
        "quiero corregir",
        "corregir",
        "corrige",
        "cambiar",
        "cambia",
        "me equivoque",
        "me equivoqué",
        "otro carro",
        "otro vehiculo",
        "otro vehículo",
        "otra ubicacion",
        "otra ubicación",
        "la ubicacion es",
        "la ubicación es",
        "el carro es",
        "el vehiculo es",
        "el vehículo es",
        "el año es",
    }

    return any(phrase in normalized_message for phrase in correction_phrases)

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
    intent = (ai_result.get("intent") or "unknown").strip()
    customer_leaves_old_battery = parse_bool(
        ai_result.get("customer_leaves_old_battery"),
        default=bool(session.customer_leaves_old_battery),
    )
    try:
        selected_catalog_option = int(ai_result.get("selected_catalog_option") or 0)
    except (TypeError, ValueError):
        selected_catalog_option = 0
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
        if intent == "accept_recommended_battery":
            return (
                "payment_link_sent",
                True,
                "",
                {
                    "step": "payment_link_sent",
                    "customer_leaves_old_battery": customer_leaves_old_battery,
                },
            )

        if intent == "ask_price_without_old_battery":
            return (
                "catalog_sent",
                True,
                "",
                {
                    "step": "catalog_sent",
                    "customer_leaves_old_battery": False,
                },
            )

        if intent == "request_more_options":
            return (
                "more_catalog_sent",
                True,
                "",
                {"step": "more_catalog_sent"},
            )

        if intent == "request_advisor":
            return (
                "advisor_handoff",
                True,
                "Claro que sí. En breve un asesor de Mega Baterías continuará contigo para ayudarte. 🔋🚗",
                {"step": "advisor_handoff"},
            )

        if any(word in normalized_message for word in [
            "acepto",
            "aceptar",
            "esa",
            "esa esta bien",
            "esa está bien",
            "me sirve",
            "quiero esa",
            "tomar esa",
            "continuar",
            "siga",
            "1",
            "opcion 1",
            "opción 1",
            "la 1",
            "quiero la 1",
            "comprar",
            "quiero comprar",
        ]):
            leaves_old_battery = not any(word in normalized_message for word in [
                "me quedo con la bateria",
                "me quedo con la batería",
                "me quedo con la vieja",
                "conservar la bateria",
                "conservar la batería",
                "conservo la vieja",
                "sin entregar",
                "no entrego",
                "no dejo",
            ])
            return (
                "payment_link_sent",
                True,
                "",
                {
                    "step": "payment_link_sent",
                    "customer_leaves_old_battery": leaves_old_battery,
                },
            )

        if any(word in normalized_message for word in [
            "mas opciones",
            "más opciones",
            "ver mas",
            "ver más",
            "otras",
            "otra",
            "otra opcion",
            "otra opción",
            "opciones",
        ]):
            return (
                "more_catalog_sent",
                True,
                "",
                {"step": "more_catalog_sent"},
            )

        if any(word in normalized_message for word in [
            "asesor",
            "persona",
            "humano",
            "vendedor",
            "llamar",
            "llamada",
        ]):
            return (
                "advisor_handoff",
                True,
                "Claro que sí. En breve un asesor de Mega Baterías continuará contigo para ayudarte. 🔋🚗",
                {"step": "advisor_handoff"},
            )

        return (
            "catalog_sent",
            True,
            (
                "Para continuar, puedes responder: "
                "acepto esta opción, ver más opciones o quiero hablar con un asesor. 🔋🚗"
            ),
            {"step": "catalog_sent"},
        )

    if session.step in {"more_options_sent", "more_catalog_sent"}:
        if intent == "request_more_options":
            return (
                session.step,
                True,
                (
                    "Claro. Te comparto nuevamente las opciones disponibles para que elijas "
                    "la que prefieras o me digas si quieres hablar con un asesor. 🔋🚗"
                ),
                {"step": session.step},
            )

        if intent == "request_advisor":
            return (
                "advisor_handoff",
                True,
                "Claro que sí. En breve un asesor de Mega Baterías continuará contigo para ayudarte. 🔋🚗",
                {"step": "advisor_handoff"},
            )

        clear_option_selected = (
            1 <= selected_catalog_option <= 3
            or normalized_message in {"1", "2", "3"}
            or any(word in normalized_message for word in [
                "opcion 1",
                "opción 1",
                "la 1",
                "numero 1",
                "número 1",
                "opcion 2",
                "opción 2",
                "la 2",
                "numero 2",
                "número 2",
                "opcion 3",
                "opción 3",
                "la 3",
                "numero 3",
                "número 3",
            ])
        )

        if clear_option_selected:
            leaves_old_battery = not any(word in normalized_message for word in [
                "me quedo con la bateria",
                "me quedo con la batería",
                "me quedo con la vieja",
                "conservar la bateria",
                "conservar la batería",
                "conservo la vieja",
                "sin entregar",
                "no entrego",
                "no dejo",
            ])
            if intent == "ask_price_without_old_battery":
                return (
                    session.step,
                    True,
                    "",
                    {
                        "step": session.step,
                        "customer_leaves_old_battery": False,
                    },
                )

            return (
                "payment_link_sent",
                True,
                "",
                {
                    "step": "payment_link_sent",
                    "customer_leaves_old_battery": (
                        customer_leaves_old_battery
                        if intent in {"select_catalog_option", "accept_recommended_battery"}
                        else leaves_old_battery
                    ),
                },
            )

        if any(word in normalized_message for word in [
            "asesor",
            "persona",
            "humano",
            "vendedor",
        ]):
            return (
                "advisor_handoff",
                True,
                "Claro que sí. En breve un asesor de Mega Baterías continuará contigo para ayudarte. 🔋🚗",
                {"step": "advisor_handoff"},
            )

        return (
            session.step,
            True,
            (
                "Para continuar, dime cuál opción prefieres: opción 1, opción 2, "
                "opción 3, o si quieres hablar con un asesor. 🔋🚗"
            ),
            {"step": session.step},
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
            intent,
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
    intent: str = "",
) -> tuple[str, bool, str, str, str, str]:

    if message_confirms_data(normalized_message, intent):
        return (
            "catalog_sent",
            True,
            "",
            current_name,
            current_vehicle,
            current_location,
        )

    if message_requests_data_correction(normalized_message, intent):
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
