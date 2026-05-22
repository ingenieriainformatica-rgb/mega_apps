# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime
from textwrap import dedent
from typing import Any
from zoneinfo import ZoneInfo
import random
from odoo import fields  # type: ignore


_logger = logging.getLogger(__name__)

COLOMBIA_TZ = ZoneInfo("America/Bogota")

CONFIRMATION_YES = {"si", "sí", "s", "correcto", "ok", "listo", "confirmo"}
CONFIRMATION_NO = {"no", "n", "incorrecto", "corregir"}

ALLOWED_STEPS = {
    "ask_name",
    "ask_vehicle",
    "ask_location",
    "confirm_data",
    "advisor_handoff",
    "done",
}

MISSING_PHONE_REPLY = "No fue posible identificar tu número de WhatsApp."

NO_ACTIVE_SESSION_REPLY = (
    "No encontré una sesión activa. Escríbeme nuevamente para iniciar la atención."
)

CONFIRMATION_RETRY_REPLY = (
    "Por favor respóndeme únicamente con Sí o No para confirmar si los datos están correctos."
)

RESET_SESSION_REPLY = (
    "Sin problema. Vamos a corregir la información. ¿Me regalas por favor tu nombre?"
)

TERMINAL_STEPS = {"advisor_handoff", "done"}

SESSION_REOPEN_MINUTES = 60 * 24 * 8

NEW_SESSION_KEYWORDS = {
    "otra batería",
    "otra bateria",
    "nueva batería",
    "nueva bateria",
    "nueva cotización",
    "nueva cotizacion",
    "otro carro",
    "otro vehículo",
    "otro vehiculo",
    "reiniciar",
    "empezar de nuevo",
}

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

    messages = [
        f"""
        Hola, muy {greeting}. Gracias por comunicarte con Mega Baterías. 🔋🚗
        Te habla Moisés Castrillón.

        Con gusto te ayudo a encontrar la batería más adecuada para tu vehículo, según la referencia, disponibilidad y ubicación.

        Para iniciar la asesoría, ¿me confirmas por favor tu nombre?
        """,
        f"""
        Muy {greeting}. Bienvenido a Mega Baterías. 🚗🔋
        Te habla Moisés Castrillón.

        Estoy aquí para ayudarte a cotizar la batería ideal para tu vehículo y validar la mejor opción disponible.

        Para atenderte de manera personalizada, ¿me regalas por favor tu nombre?
        """,
        f"""
        Hola, muy {greeting}. Gracias por escribirnos a Mega Baterías. 🔋
        Soy Moisés Castrillón y con gusto te voy a asesorar.

        Te ayudaré a revisar la mejor alternativa de batería de acuerdo con tu vehículo y ubicación.

        Para comenzar, ¿me compartes por favor tu nombre?
        """,
        f"""
        Muy {greeting}. Gracias por contactar a Mega Baterías. 🚗🔋
        Te habla Moisés Castrillón.

        Con gusto revisamos la opción de batería que mejor se ajuste a tu vehículo, disponibilidad y necesidad.

        Para brindarte una atención más personalizada, ¿me confirmas por favor tu nombre?
        """,
    ]

    return dedent(random.choice(messages)).strip()


def get_confirmation_message(session) -> str:
    name = session.customer_name or "No registrado"
    vehicle = session.vehicle_info or "No registrado"
    location = session.location or "No registrada"

    return dedent(
        f"""
        Perfecto {name}, por favor confirma si estos datos están correctos:

        Nombre: {name}
        Vehículo: {vehicle}
        Ubicación: {location}

        ¿La información es correcta? Responde Sí o No.
        """
    ).strip()


def advisor_handoff_reply(name: str | None) -> str:
    return (
        f"Excelente {name or 'señor/a'}, ya tengo tus datos confirmados. "
        "En breve un asesor de Mega continuará contigo para recomendarte la mejor batería. 🔋🚗"
    )


def get_ai_instruction(session, message: str) -> str:
    return dedent(
        f"""
        Eres un asesor virtual de Mega Baterías en Medellín.

        Tu tarea es interpretar el mensaje del cliente y ayudar a capturar datos para cotizar una batería de vehículo.

        Debes devolver SOLO JSON válido con esta estructura:

        {{
          "customer_name": "",
          "vehicle_info": "",
          "location": "",
          "intent": "",
          "confidence": 0,
          "next_step": "",
          "should_send": true,
          "reply": ""
        }}

        Reglas:
        - No inventes datos.
        - Si el cliente da nombre, extrae customer_name.
        - Si menciona marca, modelo, línea o año del vehículo, extrae vehicle_info.
        - Si menciona barrio, ciudad o ubicación, extrae location.
        - Si busca batería, intent debe ser "battery_quote".
        - Si falta nombre, next_step debe ser "ask_name".
        - Si next_step es "ask_name", el campo reply debe ser EXACTAMENTE este texto:

        {get_welcome_message()}

        - Si falta vehículo, next_step debe ser "ask_vehicle".
        - Si falta ubicación, next_step debe ser "ask_location".
        - Si están nombre, vehículo y ubicación, next_step debe ser "confirm_data".
        - Si el cliente confirma los datos con sí, ok, correcto o listo, next_step debe ser "advisor_handoff".
        - Si el cliente pide asesor humano, next_step debe ser "advisor_handoff".
        - No des precios.
        - No confirmes disponibilidad.
        - Responde corto y natural para WhatsApp.
        - Devuelve únicamente JSON válido, sin markdown, sin explicación y sin texto adicional.

        Estado actual: {session.step}
        Nombre actual: {session.customer_name or ""}
        Vehículo actual: {session.vehicle_info or ""}
        Ubicación actual: {session.location or ""}
        Mensaje del cliente: {message}
        """
    ).strip()


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
    vehicle_info = (ai_result.get("vehicle_info") or "").strip()
    location = (ai_result.get("location") or "").strip()
    next_step = (ai_result.get("next_step") or session.step).strip()
    reply = (ai_result.get("reply") or "").strip()
    should_send = bool(ai_result.get("should_send", True))

    if next_step not in ALLOWED_STEPS:
        next_step = session.step

    current_name = customer_name or session.customer_name or ""
    current_vehicle = vehicle_info or session.vehicle_info or ""
    current_location = location or session.location or ""
    normalized_message = normalize_answer(session.last_message)

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

    elif next_step not in {"confirm_data", "advisor_handoff"}:
        next_step = "confirm_data"
        should_send = True

    vals = build_session_vals(
        next_step,
        current_name,
        current_vehicle,
        current_location,
    )

    return next_step, should_send, reply, vals


def resolve_confirmation_from_ai(
    normalized_message: str,
    current_name: str,
    current_vehicle: str,
    current_location: str,
) -> tuple[str, bool, str, str, str, str]:
    if normalized_message in CONFIRMATION_YES:
        return (
            "advisor_handoff",
            True,
            advisor_handoff_reply(current_name),
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
