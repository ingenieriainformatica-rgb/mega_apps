# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime
from textwrap import dedent
from typing import Any
from zoneinfo import ZoneInfo


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

    if session:
        write_last_message(session, message, phone_number_id)
        return session, False

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
    return dedent(
        f"""
        Hola, muy {get_colombia_greeting()}. Un gusto saludarte.
        Te habla Moisés Castrillón, asesor de Mega Baterías. 🔋🚗

        ¿Me regalas por favor tu nombre?
        Y cuéntame, ¿qué tipo de batería estás buscando y para qué vehículo la necesitas?

        Estoy atento para asesorarte y recomendarte la mejor opción según tu vehículo y presupuesto. 👍
        """
    ).strip()


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
