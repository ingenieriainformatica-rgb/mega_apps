# -*- coding: utf-8 -*-

import json
import logging
import re
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


VEHICLE_BRAND_CORRECTIONS = {
    "masda": "Mazda",
    "masdaa": "Mazda",
    "masd": "Mazda",
    "madza": "Mazda",
    "mazda": "Mazda",
    "chebrolet": "Chevrolet",
    "chevrolet": "Chevrolet",
    "hiunday": "Hyundai",
    "hyundai": "Hyundai",
    "renol": "Renault",
    "renaul": "Renault",
    "renault": "Renault",
    "toyta": "Toyota",
    "toyota": "Toyota",
    "wolsvagen": "Volkswagen",
    "volkswagen": "Volkswagen",
    "nisan": "Nissan",
    "nissan": "Nissan",
    "kia": "Kia",
    "ford": "Ford",
}


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

def extract_known_location_from_message(message: str | None) -> str:
    normalized = normalize_text(message or "")

    if not normalized:
        return ""

    known_locations = list(COVERAGE_LOCATIONS) + list(OUT_OF_COVERAGE_LOCATIONS)
    for location in known_locations:
        if normalize_text(location) in normalized:
            return location

    return ""

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

def clean_text(value: Any) -> str:
    return str(value or "").strip()

def is_doubtful_customer_name(value: str | None) -> bool:
    normalized = normalize_text(value or "")
    return normalized in {
        "",
        "yo",
        "cliente",
        "hola",
        "buenas",
        "buenos dias",
        "buenas tardes",
        "buenas noches",
        "senor",
        "senora",
        "sr",
        "sra",
    }

def is_valid_customer_name(value: str | None) -> bool:
    name = clean_text(value)

    if is_doubtful_customer_name(name):
        return False

    parts = [part for part in name.replace("-", " ").split() if part]
    if not 1 <= len(parts) <= 4:
        return False

    return all(any(char.isalpha() for char in part) for part in parts)

def normalize_next_required_field(value: str | None) -> str:
    normalized = normalize_text(value or "")
    aliases = {
        "name": "customer_name",
        "nombre": "customer_name",
        "marca": "vehicle_brand",
        "modelo": "vehicle_model",
        "linea": "vehicle_model",
        "ano": "vehicle_year",
        "anio": "vehicle_year",
        "ciudad": "city",
        "ubicacion": "location",
        "barrio": "location",
        "placa": "plate",
    }
    return aliases.get(normalized, normalized)

def step_from_next_required_field(field_name: str | None) -> str:
    field_name = normalize_next_required_field(field_name)

    if field_name == "customer_name":
        return "ask_name"

    if field_name in {"vehicle_brand", "vehicle_model", "vehicle_year", "vehicle_type"}:
        return "ask_vehicle"

    if field_name in {"city", "location", "neighborhood", "plate"}:
        return "ask_location"

    return ""

def normalize_vehicle_brand(value: str | None) -> str:
    brand = clean_text(value)
    normalized = normalize_text(brand)
    return VEHICLE_BRAND_CORRECTIONS.get(normalized, brand)

def is_doubtful_vehicle_model(value: str | None, customer_name: str | None = "") -> bool:
    model = clean_text(value)
    normalized = normalize_text(model)
    normalized_name = normalize_text(customer_name or "")

    if not normalized:
        return True

    if normalized_name and normalized_name in normalized:
        return True

    doubtful_values = {
        "y",
        "yo",
        "tengo",
        "tengo un",
        "tengo una",
        "carro",
        "vehiculo",
        "vehículo",
        "modelo",
        "linea",
        "línea",
    }
    return normalized in doubtful_values

def extract_vehicle_fields_from_message(message: str | None) -> dict[str, str]:
    normalized = normalize_text(message or "")

    if not normalized:
        return {}

    brand_match = None
    brand = ""
    for alias, corrected_brand in VEHICLE_BRAND_CORRECTIONS.items():
        match = re.search(rf"\b{re.escape(alias)}\b", normalized)
        if match:
            brand_match = match
            brand = corrected_brand
            break

    if not brand or not brand_match:
        return {}

    year_match = re.search(r"\b(?:19|20)\d{2}\b", normalized)
    year = year_match.group(0) if year_match else ""

    model_text = normalized[brand_match.end():]
    if year:
        model_text = re.sub(rf"\b{re.escape(year)}\b", " ", model_text)
    model_text = re.sub(r"[^a-z0-9\s-]", " ", model_text)

    stopwords = {
        "tengo",
        "un",
        "una",
        "carro",
        "vehiculo",
        "vehículo",
        "modelo",
        "linea",
        "línea",
        "es",
        "el",
        "la",
        "mi",
        "para",
        "bateria",
        "batería",
        "y",
        "quiero",
        "necesito",
    }
    model_parts = [
        part
        for part in model_text.split()
        if part and part not in stopwords
    ]

    result = {"vehicle_brand": brand}
    if model_parts:
        result["vehicle_model"] = " ".join(model_parts[:2])
    if year:
        result["vehicle_year"] = year

    return result

def get_time_based_greeting() -> str:
    current_hour = datetime.now(COLOMBIA_TZ).hour

    if current_hour < 12:
        return "buen día"
    if current_hour < 18:
        return "buena tarde"
    return "buena noche"

def get_simple_full_welcome() -> str:
    greeting = get_time_based_greeting()
    return (
        f"Hola {greeting}, te habla Moisés Castrillón, asesor experto en baterías MAC.\n\n"
        "Te puedo asesorar en la aplicación correcta de baterías para tu automóvil, "
        "buses, maquinaria amarilla y plantas eléctricas.\n\n"
        "Te prestamos rápido servicio a domicilio e instalación técnica de la batería "
        "en Medellín y su área metropolitana.\n\n"
        "Atendemos automóvil, camioneta, camión, bus, maquinaria amarilla y plantas eléctricas.\n\n"
        "¿Cuál es tu nombre y para qué vehículo requieres la batería?"
    )

def normalize_ai_result(ai_result: dict[str, Any]) -> dict[str, Any]:
    normalized_result = dict(ai_result or {})
    brand = normalize_vehicle_brand(normalized_result.get("vehicle_brand"))
    if brand:
        normalized_result["vehicle_brand"] = brand
    return normalized_result

def get_safe_reply(
    ai_result: dict[str, Any],
    reply: str,
    session=None,
) -> tuple[str, bool]:
    safe_reply = clean_text(reply)
    if safe_reply:
        return safe_reply, False

    safe_reply = clean_text(
        ai_result.get("reply") or ai_result.get("assistant_message")
    )
    if safe_reply:
        return safe_reply, False

    _logger.warning(
        "Using fallback WhatsApp reply session=%s step=%s ai_result=%s",
        getattr(session, "id", False),
        getattr(session, "step", False),
        ai_result,
    )
    return "Con gusto te ayudamos. ¿Me compartes por favor tu nombre?", True

def get_full_welcome_intro() -> str:
    return dedent(
        """
        Hola 👋 Bienvenido a Mega Baterías.

        📍 Atendemos Medellín y Área Metropolitana.
        🕒 Horario: lunes a sábado de 7:00 a.m. a 6:00 p.m.
        🔋 Solo manejamos baterías para carros, camionetas y camiones.

        Gracias por contactarnos. Con gusto te ayudamos a cotizar la batería adecuada para tu vehículo. 🚗
        """
    ).strip()

def build_detected_data_summary(
    current_name: str = "",
    current_brand: str = "",
    current_model: str = "",
    current_year: str = "",
    current_location: str = "",
    plate: str = "",
) -> str:
    lines = []

    if current_name:
        lines.append(f"👤 Nombre: {current_name}")
    if current_brand:
        lines.append(f"🚗 Marca: {current_brand}")
    if current_model:
        lines.append(f"🚗 Modelo: {current_model}")
    if current_year:
        lines.append(f"🚗 Año: {current_year}")
    if current_location:
        lines.append(f"📍 Ubicación: {current_location}")
    if plate:
        lines.append(f"🔢 Placa: {plate}")

    if not lines:
        return ""

    return "Ya tengo registrado:\n" + "\n".join(lines)

def default_question_for_step(next_step: str, current_name: str = "") -> str:
    if next_step == "ask_name":
        return "Para empezar, ¿me cuentas por favor tu nombre?"

    if next_step == "ask_vehicle":
        prefix = f"Perfecto {current_name} 👍\n\n" if current_name else ""
        return f"{prefix}¿Me compartes por favor la marca, línea y año del vehículo?"

    if next_step == "ask_location":
        return "¿Me confirmas por favor en qué ciudad o barrio te encuentras?"

    return "Con gusto te ayudamos. ¿Me compartes por favor los datos para continuar?"

def ensure_single_welcome_reply(
    session,
    reply: str,
    next_step: str,
    current_name: str = "",
    current_brand: str = "",
    current_model: str = "",
    current_year: str = "",
    current_location: str = "",
    plate: str = "",
) -> str:
    reply = clean_text(reply)

    if bool(getattr(session, "welcome_sent", False)):
        return reply

    if reply_contains_full_welcome(reply):
        return reply

    summary = build_detected_data_summary(
        current_name=current_name,
        current_brand=current_brand,
        current_model=current_model,
        current_year=current_year,
        current_location=current_location,
        plate=plate,
    )

    question = reply or default_question_for_step(next_step, current_name)
    parts = [get_full_welcome_intro()]

    if summary:
        parts.append(summary)
    if question:
        parts.append(question)

    return "\n\n".join(parts).strip()

def mark_welcome_sent_on_session(session, message_sent: bool) -> bool:
    if not message_sent or bool(getattr(session, "welcome_sent", False)):
        return False

    if hasattr(session, "write"):
        session.write({"welcome_sent": True})
    else:
        setattr(session, "welcome_sent", True)

    return True

def reply_contains_full_welcome(reply: str | None) -> bool:
    normalized = normalize_text(reply or "")
    required_fragments = (
        "bienvenido a mega baterias",
        "atendemos medellin",
        "horario",
        "carros",
    )
    return all(fragment in normalized for fragment in required_fragments)

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
        "welcome_sent": bool(getattr(session, "welcome_sent", False)),
        "customer_name": session.customer_name or "",
        "vehicle_brand": getattr(session, "vehicle_brand", "") or "",
        "vehicle_model": getattr(session, "vehicle_model", "") or "",
        "vehicle_year": getattr(session, "vehicle_year", "") or "",
        "vehicle_type": getattr(session, "vehicle_type", "") or "",
        "vehicle_info": session.vehicle_info or "",
        "city": getattr(session, "city", "") or "",
        "neighborhood": getattr(session, "neighborhood", "") or "",
        "location": session.location or "",
        "plate": getattr(session, "plate", "") or "",
        "battery_request": bool(getattr(session, "battery_request", False)),
        "relevant_data": getattr(session, "relevant_data", "") or "",
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
    ai_result = normalize_ai_result(ai_result)

    customer_name = clean_text(ai_result.get("customer_name"))
    vehicle_info = build_vehicle_info_from_ai(
        ai_result,
        fallback=session.vehicle_info or "",
    )
    city = clean_text(ai_result.get("city"))
    location = clean_text(ai_result.get("location")) or city
    conversation_summary = clean_text(ai_result.get("conversation_summary"))
    intent = clean_text(ai_result.get("intent") or "unknown")
    customer_leaves_old_battery = parse_bool(
        ai_result.get("customer_leaves_old_battery"),
        default=bool(session.customer_leaves_old_battery),
    )
    try:
        selected_catalog_option = int(ai_result.get("selected_catalog_option") or 0)
    except (TypeError, ValueError):
        selected_catalog_option = 0
    next_step = clean_text(ai_result.get("next_step") or session.step)
    next_required_step = step_from_next_required_field(ai_result.get("next_required_field"))
    if next_required_step:
        next_step = next_required_step

    reply = clean_text(ai_result.get("reply") or ai_result.get("assistant_message"))
    should_send = bool(ai_result.get("should_send", True))

    if next_step not in ALLOWED_STEPS:
        next_step = session.step

    if customer_name and not is_valid_customer_name(customer_name):
        customer_name = ""
        if not session.customer_name:
            next_step = "ask_name"
            should_send = True
            reply = "¿Me confirmas por favor tu nombre para continuar?"

    current_name = customer_name or session.customer_name or ""
    current_brand = clean_text(ai_result.get("vehicle_brand")) or getattr(session, "vehicle_brand", "") or ""
    current_model = clean_text(ai_result.get("vehicle_model")) or getattr(session, "vehicle_model", "") or ""
    current_year = clean_text(ai_result.get("vehicle_year")) or getattr(session, "vehicle_year", "") or ""
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
        vals.update(build_progressive_session_vals(session, ai_result))

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

    elif not (current_brand and current_model and current_year):
        next_step = "ask_vehicle"
        should_send = True
        reply = reply or f"Gracias {current_name}. ¿Me compartes la marca, línea y año del vehículo? 🔋🚗"

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
    vals.update(build_progressive_session_vals(session, ai_result))

    if conversation_summary and "conversation_summary" in session._fields:
        vals["conversation_summary"] = conversation_summary[:500]

    if should_send:
        reply, _used_fallback = get_safe_reply(ai_result, reply, session=session)
        reply = ensure_single_welcome_reply(
            session,
            reply,
            next_step,
            current_name=current_name,
            current_brand=current_brand,
            current_model=current_model,
            current_year=current_year,
            current_location=current_location,
            plate=clean_text(ai_result.get("plate")) or getattr(session, "plate", "") or "",
        )

    return next_step, should_send, reply, vals

def build_simple_ai_session_update(
    session,
    ai_result: dict[str, Any],
) -> tuple[str, bool, str, dict[str, Any]]:
    ai_result = normalize_ai_result(ai_result)

    customer_name = clean_text(ai_result.get("customer_name"))
    if customer_name and not is_valid_customer_name(customer_name):
        customer_name = ""

    message_vehicle = extract_vehicle_fields_from_message(
        getattr(session, "last_message", "")
    )
    current_name = customer_name or session.customer_name or ""
    current_brand = (
        clean_text(ai_result.get("vehicle_brand"))
        or getattr(session, "vehicle_brand", "")
        or message_vehicle.get("vehicle_brand", "")
    )
    current_brand = normalize_vehicle_brand(current_brand)
    current_model = (
        clean_text(ai_result.get("vehicle_model"))
        or getattr(session, "vehicle_model", "")
        or message_vehicle.get("vehicle_model", "")
    )
    if is_doubtful_vehicle_model(current_model, current_name):
        current_model = ""
    current_year = (
        clean_text(ai_result.get("vehicle_year"))
        or getattr(session, "vehicle_year", "")
        or message_vehicle.get("vehicle_year", "")
    )
    city = clean_text(ai_result.get("city"))
    location = clean_text(ai_result.get("location")) or city
    if not location:
        location = extract_known_location_from_message(getattr(session, "last_message", ""))
    current_location = location or session.location or ""
    current_vehicle = build_vehicle_info_from_ai(
        {
            **ai_result,
            "vehicle_brand": current_brand,
            "vehicle_model": current_model,
            "vehicle_year": current_year,
        },
        fallback=session.vehicle_info or "",
    )
    conversation_summary = clean_text(ai_result.get("conversation_summary"))

    missing_name = not current_name
    missing_location = not current_location
    missing_vehicle = not (current_brand and current_model and current_year)
    welcome_reply = get_simple_full_welcome()

    vehicle_parts = [part for part in [current_brand, current_model, current_year] if part]
    vehicle_label = " ".join(vehicle_parts).strip()
    has_vehicle_data = bool(vehicle_parts)

    def with_vehicle_context(question: str) -> str:
        if not has_vehicle_data:
            return question

        intro = f"Listo, tengo tu {vehicle_label}." if vehicle_label else "Listo, ya tengo los datos del vehículo."
        return f"{intro}\n\n{question}"

    def final_handoff_reply() -> str:
        vehicle_text = f" tu {vehicle_label}" if vehicle_label else " los datos de tu vehículo"
        location_text = f" en {current_location}" if current_location else ""
        return (
            f"Listo, {current_name}. Ya tengo{vehicle_text}{location_text}. "
            "En breve un asesor de Mega Baterías continuará contigo para indicarte la batería adecuada para tu carro."
        )

    if current_location and is_out_of_coverage(current_location):
        next_step = "out_of_coverage"
        reply = get_out_of_coverage_message()
    elif missing_name:
        next_step = "ask_name"
        reply = with_vehicle_context("Indícame tu nombre, por favor.") if has_vehicle_data else welcome_reply
    elif missing_location:
        next_step = "ask_location"
        reply = f"{current_name}, gracias. Cuéntame, ¿te encuentras en Medellín o en algún municipio cercano?"
    elif missing_vehicle:
        next_step = "ask_vehicle"
        missing_vehicle_fields = []
        if not current_brand:
            missing_vehicle_fields.append("marca")
        if not current_model:
            missing_vehicle_fields.append("línea/modelo")
        if not current_year:
            missing_vehicle_fields.append("año")

        if len(missing_vehicle_fields) == 3:
            reply = (
                "Muchas gracias por tu información. ¿Qué carro manejas? "
                "Indícame la marca, línea/modelo y año para indicarte la batería adecuada para tu carro."
            )
        else:
            missing_text = ", ".join(missing_vehicle_fields)
            reply = with_vehicle_context(
                "Muchas gracias por tu información. "
                f"Para continuar, indícame por favor {missing_text} del vehículo."
            )
    else:
        next_step = "advisor_handoff"
        reply = final_handoff_reply()

    vals = build_session_vals(
        next_step,
        current_name,
        current_vehicle,
        current_location,
    )
    progressive_ai_result = {
        **ai_result,
        "vehicle_brand": current_brand,
        "vehicle_model": current_model,
        "vehicle_year": current_year,
    }
    vals.update(build_progressive_session_vals(session, progressive_ai_result))
    vals["step"] = next_step

    if not bool(getattr(session, "welcome_sent", False)) and "welcome_sent" in session._fields:
        vals["welcome_sent"] = True

    if conversation_summary and "conversation_summary" in session._fields:
        vals["conversation_summary"] = conversation_summary[:500]

    return next_step, True, reply, vals

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

    return vals

def build_progressive_session_vals(session, ai_result: dict[str, Any]) -> dict[str, Any]:
    ai_result = normalize_ai_result(ai_result)
    vals: dict[str, Any] = {}

    field_map = {
        "vehicle_brand": "vehicle_brand",
        "vehicle_model": "vehicle_model",
        "vehicle_year": "vehicle_year",
        "vehicle_type": "vehicle_type",
        "city": "city",
        "neighborhood": "neighborhood",
        "plate": "plate",
        "relevant_data": "relevant_data",
    }

    for result_key, session_field in field_map.items():
        if session_field not in session._fields:
            continue
        value = clean_text(ai_result.get(result_key))
        if value:
            vals[session_field] = value

    if "battery_request" in session._fields:
        vals["battery_request"] = parse_bool(
            ai_result.get("battery_request"),
            default=bool(session.battery_request),
        )

    city = clean_text(ai_result.get("city"))
    location = clean_text(ai_result.get("location"))
    neighborhood = clean_text(ai_result.get("neighborhood") or ai_result.get("barrio"))

    if not location:
        location = " ".join(part for part in [neighborhood, city] if part).strip()

    if location and "location" in session._fields:
        vals["location"] = location

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
