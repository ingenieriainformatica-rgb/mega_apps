# -*- coding: utf-8 -*-

import json
import re
import logging
from datetime import datetime
from textwrap import dedent
from typing import Any
import random
from odoo import fields  # type: ignore
# from odoo.tools import html_escape  # type: ignore
from markupsafe import Markup, escape

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
    LEAD_BRAND_FIELD,
    LEAD_MODEL_FIELD,
    LEAD_YEAR_FIELD,
    COLOMBIA_TZ,
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


def get_out_of_coverage_message() -> str:
    return (
        "¡Recuerda que en Mega Baterías estamos ubicados en la ciudad de Medellín "
        "y actualmente contamos con cobertura únicamente en Medellín y su área metropolitana! 🔋🚗\n\n"
        "Además de baterías, también ofrecemos servicios como alineación y balanceo, "
        "reparación de frenos y suspensión, venta de llantas y mantenimientos preventivos "
        "y correctivos para tu vehículo.\n\n"
        "Si necesitas algo más, no dudes en contactarnos. "
        "¡Gracias por confiar en nosotros y que tengas un excelente día! 🙌"
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
        Hola, muy {greeting}. 👋
        Gracias por comunicarte con Mega Baterías. 🔋🚗

        Estamos listos para ayudarte a encontrar la batería ideal para tu carro o camión según tu vehículo y ubicación.

        ¿Me regalas por favor tu nombre?
        """,

        f"""
        Muy {greeting}. Bienvenido a Mega Baterías. 🔋

        Con gusto te ayudamos a cotizar la batería adecuada para tu carro o camión.

        Para comenzar, ¿me compartes tu nombre?
        """,

        f"""
        Hola, muy {greeting}. 👋
        Estás hablando con el equipo de Mega Baterías. 🚗🔋

        Podemos ayudarte a validar la mejor opción de batería según referencia, disponibilidad y ubicación.

        ¿Me indicas por favor tu nombre?
        """,

        f"""
        Muy {greeting}. Gracias por escribirnos. 🔋🚗

        Estamos atentos para ayudarte a encontrar la batería adecuada para tu carro o camión.

        Para iniciar la asesoría, ¿me compartes tu nombre?
        """,

        f"""
        Hola, muy {greeting}. 👋
        Gracias por contactar a Mega Baterías.

        Te ayudamos a revisar la batería ideal para tu vehículo y validar disponibilidad en Medellín y área metropolitana.

        ¿Cuál es tu nombre?
        """,

        f"""
        Muy {greeting}. 🚗🔋

        En Mega Baterías estamos listos para asesorarte con la mejor opción de batería para tu carro o camión.

        ¿Me confirmas tu nombre?
        """,

        f"""
        Hola, muy {greeting}. 👋
        Gracias por escribir a Mega Baterías. 🔋

        Podemos ayudarte con la cotización y recomendación de batería para tu vehículo.

        ¿Me compartes por favor tu nombre?
        """,

        f"""
        Muy {greeting}. Bienvenido. 🚗

        Con gusto revisamos contigo la mejor batería para tu carro o camión según tu necesidad y ubicación.

        Para comenzar, ¿me indicas tu nombre?
        """,

        f"""
        Hola, muy {greeting}. 🔋🚗

        Somos el equipo de Mega Baterías y estamos atentos para ayudarte con tu cotización.

        ¿Me regalas por favor tu nombre?
        """,

        f"""
        Muy {greeting}. 👋
        Gracias por comunicarte con Mega Baterías.

        Estamos listos para ayudarte a encontrar la mejor opción de batería para tu carro o camión.

        ¿Cuál es tu nombre?
        """,
    ]

    return dedent(random.choice(messages)).strip()

def get_confirmation_message(session) -> str:
    name = session.customer_name or "No registrado"
    vehicle = session.vehicle_info or "No registrado"
    location = session.location or "No registrada"

    messages = [
        f"""
        Perfecto {name}, ya tengo la información inicial para continuar con la asesoría:

        Nombre: {name}
        Vehículo: {vehicle}
        Ubicación: {location}

        ¿Me confirmas por favor si estos datos están correctos? Responde Sí o No.
        """,
        f"""
        Gracias {name}. Con estos datos podemos revisar mejor la opción de batería:

        Nombre: {name}
        Vehículo: {vehicle}
        Ubicación: {location}

        ¿La información está correcta? Respóndeme Sí o No, por favor.
        """,
        f"""
        Muy bien {name}, ya registré estos datos para avanzar con la cotización:

        Nombre: {name}
        Vehículo: {vehicle}
        Ubicación: {location}

        ¿Me ayudas confirmando si todo está correcto? Responde Sí o No.
        """,
    ]
    return dedent(random.choice(messages)).strip()


def advisor_handoff_reply(name: str | None) -> str:
    customer = name or "señor/a"

    messages = [
        f"""
        Perfecto {customer}, ya tenemos tus datos registrados correctamente. 🔋🚗

        En unos momentos uno de nuestros asesores continuará contigo para recomendarte la mejor opción según tu vehículo y ubicación.

        ¡Gracias por comunicarte con Mega Baterías!
        """,

        f"""
        Excelente {customer}. Ya validamos tu información correctamente. ✅

        Ahora uno de nuestros asesores especializados continuará la atención para ayudarte con la mejor alternativa para tu vehículo.

        Gracias por confiar en Mega Baterías. 🔋
        """,

        f"""
        Muchas gracias {customer}. Ya dejamos registrada toda tu información. 🚗🔋

        En breve un asesor de Mega Baterías seguirá contigo para ayudarte con la batería más adecuada para tu vehículo.

        ¡Quedamos atentos!
        """,
    ]

    return dedent(random.choice(messages)).strip()


def get_ai_instruction(session, message: str) -> str:
    return dedent(
        f"""
        # CONTEXTO

        Mega Baterías es una empresa ubicada en Medellín, Colombia.
        Atiende clientes por WhatsApp para cotizar baterías para carros y camiones.

        Cobertura actual:
        Medellín y área metropolitana:
        Medellín, Bello, Itagüí, Envigado, Sabaneta, La Estrella, Caldas,
        Copacabana, Girardota y Barbosa.

        La conversación hace parte de un flujo conectado con Odoo CRM.
        El objetivo es capturar datos correctos del cliente para crear o actualizar un lead
        y luego pasarlo a un asesor humano.

        ----------------------------------------------------------------

        # ROL

        Actúas como asesor virtual profesional de Mega Baterías.

        Debes responder:
        - corto
        - natural
        - amable
        - comercial
        - claro
        - como atención real por WhatsApp

        Nunca menciones que eres IA, modelo, bot o sistema automático.

        ----------------------------------------------------------------

        # ACCIÓN PRINCIPAL

        Debes interpretar el mensaje del cliente y devolver únicamente un JSON válido con:
        - datos extraídos
        - siguiente paso del flujo
        - respuesta sugerida para WhatsApp
        - resumen actualizado de la conversación

        ----------------------------------------------------------------

        # PASOS DEL FLUJO

        Pasos válidos:
        - ask_name
        - ask_vehicle
        - ask_location
        - confirm_data
        - advisor_handoff
        - out_of_coverage
        - done

        Reglas estrictas:
        - NO avances al siguiente paso si el paso actual no está completo.
        - NO pidas ubicación si todavía falta el vehículo.
        - NO confirmes datos si falta nombre, vehículo o ubicación.
        - NO pases al asesor si los datos no han sido confirmados.
        - Si falta nombre, pide solo el nombre.
        - Si falta vehículo, pide marca, línea/modelo y año.
        - Si falta ubicación, pide barrio, municipio o zona.
        - Si ya están nombre, vehículo y ubicación, next_step debe ser confirm_data.
        - Si el cliente confirma con sí, ok, correcto o listo, next_step debe ser advisor_handoff.
        - Si ya existe un vehículo actual y el cliente solo complementa un dato faltante, conserva el vehículo actual y complétalo. No vuelvas a pedir marca/modelo/año si ya fueron entregados.

        ----------------------------------------------------------------

        # REGLAS DE NEGOCIO

        - Solo se atienden baterías para carros y camiones.
        - No se atienden baterías para motos.
        - No se venden celulares, electrodomésticos ni otros productos.
        - No des precios.
        - No confirmes disponibilidad.
        - No prometas cobertura.
        - No inventes datos.

        Si el cliente está fuera de Medellín o área metropolitana:
        - next_step debe ser "out_of_coverage"
        - should_send debe ser true
        - location debe contener la ubicación detectada
        - reply debe indicar amablemente que actualmente solo hay cobertura en Medellín y área metropolitana.

        ----------------------------------------------------------------

        # MANEJO DE ERRORES DE ESCRITURA

        Puedes corregir errores evidentes si la intención es clara.

        Ejemplos de marcas:
        - "masda" probablemente es "Mazda"
        - "chebrolet" probablemente es "Chevrolet"
        - "renol" probablemente es "Renault"
        - "volswagen" probablemente es "Volkswagen"
        - "hiunday" probablemente es "Hyundai"

        Ejemplos de nombres:
        - "jroge" probablemente es "Jorge"
        - "josee" probablemente es "José"
        - "andres" puede guardarse como "Andrés"
        - "maria" puede guardarse como "María"
        - "alejndro" probablemente es "Alejandro"

        Reglas:
        - Si no estás seguro, deja el dato vacío.
        - No inventes apellidos.
        - No inventes marcas, modelos ni años.
        - Usa mayúscula inicial en nombres y apellidos.

        ----------------------------------------------------------------

        # CLIENTE NO SABE LOS DATOS DEL VEHÍCULO

        Si el cliente no sabe la marca, línea/modelo o año:
        - No lo bloquees.
        - Explícale de forma breve que puede revisar la tarjeta de propiedad.
        - También puede enviar una foto de la tarjeta de propiedad o decir los datos que recuerde.
        - Mantén next_step en "ask_vehicle".
        - No avances a ask_location hasta tener al menos información útil del vehículo.

        Ejemplo de respuesta:
        "No te preocupes. Puedes revisar esos datos en la tarjeta de propiedad del vehículo. También puedes enviarnos una foto o decirme lo que recuerdes: marca, línea o año."

        ----------------------------------------------------------------

        # MANEJO DE LENGUAJE OFENSIVO

        Si el cliente escribe groserías, insultos o habla agresivo:
        - Mantén tono profesional.
        - No respondas con groserías.
        - No confrontes.
        - Continúa pidiendo el dato necesario según el paso actual.
        - Si no trae datos útiles, responde breve y amable.

        ----------------------------------------------------------------

        # EXTRACCIÓN DE DATOS

        Extrae:
        - nombre → customer_name
        - marca → vehicle_brand
        - línea/modelo → vehicle_model
        - año → vehicle_year
        - ubicación → location

        vehicle_info debe contener el vehículo completo cuando sea posible.

        Ejemplos:
        - "Mazda 3 2017"
        - "Spark GT 2019"
        - "Logan 2016"

        ----------------------------------------------------------------

        # RESUMEN DE CONVERSACIÓN

        conversation_summary:
        - máximo 300 caracteres
        - incluye nombre, vehículo, ubicación e intención
        - no copies toda la conversación
        - no inventes información

        ----------------------------------------------------------------

        # FORMATO OBLIGATORIO

        Devuelve únicamente JSON válido.
        No uses markdown.
        No expliques nada.
        No agregues texto fuera del JSON.

        {{
          "customer_name": "",
          "vehicle_info": "",
          "vehicle_brand": "",
          "vehicle_model": "",
          "vehicle_year": "",
          "location": "",
          "conversation_summary": "",
          "intent": "",
          "confidence": 0,
          "next_step": "",
          "should_send": true,
          "reply": ""
        }}

        ----------------------------------------------------------------

        # ESTADO ACTUAL

        Paso actual: {session.step}
        Nombre actual: {session.customer_name or "Sin registrar"}
        Vehículo actual: {session.vehicle_info or "Sin registrar"}
        Ubicación actual: {session.location or "Sin registrar"}
        Resumen actual: {session.conversation_summary or "Sin resumen previo"}

        ----------------------------------------------------------------

        # MENSAJE DEL CLIENTE

        {message}
        """
    ).strip()

# def get_ai_instruction(session, message: str) -> str:
#     return dedent(
#         f"""
#         Eres un asesor virtual de Mega Baterías en Medellín.

#         Tu tarea es interpretar el mensaje del cliente y ayudar a capturar datos para cotizar una batería de vehículo.

#         Debes devolver SOLO JSON válido con esta estructura:

#         {{
#           "customer_name": "",
#           "vehicle_info": "",
#           "vehicle_brand": "",
#           "vehicle_model": "",
#           "vehicle_year": "",
#           "location": "",
#           "conversation_summary": "",
#           "intent": "",
#           "confidence": 0,
#           "next_step": "",
#           "should_send": true,
#           "reply": ""
#         }}

#         Reglas:
#         - conversation_summary debe resumir en máximo 300 caracteres lo importante de la conversación.
#         - Incluye nombre, vehículo, ubicación, intención y datos útiles para continuar la venta.
#         - No copies toda la conversación.
#         - No inventes datos.
#         - Si el cliente da nombre, extrae customer_name.
#         - Si menciona marca, modelo, línea o año del vehículo, extrae vehicle_info.
#         - Si identifica la marca del vehículo, extrae vehicle_brand. Ejemplo: Mazda, Chevrolet, Renault.
#         - Si identifica la línea/modelo del vehículo, extrae vehicle_model. Ejemplo: 3, Spark GT, Logan, Twingo.
#         - Si identifica el año del vehículo, extrae vehicle_year. Ejemplo: 2018.
#         - Si no estás seguro de marca, modelo o año, déjalo vacío.
#         - Si menciona barrio, ciudad o ubicación, extrae location.
#         - Si busca batería, intent debe ser "battery_quote".
#         - Si falta nombre, next_step debe ser "ask_name".
#         - Si falta nombre y ya existe una sesión, responde corto y natural pidiendo solo el nombre.
#         - Si falta vehículo, next_step debe ser "ask_vehicle".
#         - Si falta ubicación, next_step debe ser "ask_location".
#         - Si están nombre, vehículo y ubicación, next_step debe ser "confirm_data".
#         - Si el cliente confirma los datos con sí, ok, correcto o listo, next_step debe ser "advisor_handoff".
#         - Si el cliente pide asesor humano, next_step debe ser "advisor_handoff".
#         - No des precios.
#         - No confirmes disponibilidad.
#         - Responde corto y natural para WhatsApp.
#         - Devuelve únicamente JSON válido, sin markdown, sin explicación y sin texto adicional.
#         - Mega Baterías atiende en Medellín y área metropolitana.
#         - Si el cliente pregunta por motos, celulares, electrodomésticos u otro producto diferente, responde amablemente que por ahora solo asesoras baterías para carros.
#         - Si el cliente está fuera de Medellín o área metropolitana, captura la ubicación y responde que un asesor validará cobertura antes de confirmar disponibilidad.
#         - Mega Baterías atiende baterías para carros, camiones y aplicaciones industriales, no para otros productos.
#         - Mega Baterías solo tiene cobertura en Medellín y área metropolitana.
#         - Si el cliente indica una ubicación fuera de Medellín o área metropolitana, next_step debe ser "out_of_coverage".
#         - En ese caso should_send debe ser true y reply debe indicar amablemente que por ahora no contamos con cobertura en esa zona.

#         Estado actual: {session.step}
#         Nombre actual: {session.customer_name or ""}
#         Vehículo actual: {session.vehicle_info or ""}
#         Ubicación actual: {session.location or ""}
#         Mensaje del cliente: {message}

#         Resumen actual: {session.conversation_summary or "Sin resumen previo"}
#         """
#     ).strip()

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


def clean_vehicle_text(value: str | None) -> str:
    value = (value or "").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def find_vehicle_brand(env, brand_name: str | None):
    brand_name = clean_vehicle_text(brand_name)

    if not brand_name:
        return False

    Brand = env["fleet.vehicle.model.brand"].sudo()

    brand = Brand.search([("name", "=ilike", brand_name)], limit=1)
    if brand:
        return brand

    return Brand.search([("name", "ilike", brand_name)], limit=1)


def find_vehicle_model(env, model_name: str | None, brand=None):
    model_name = clean_vehicle_text(model_name)

    if not model_name:
        return False

    Model = env["fleet.vehicle.model"].sudo()

    domain_base = []
    if brand and getattr(brand, "id", False):
        domain_base.append(("brand_id", "=", brand.id))

    # Caso ideal: modelo exacto
    model = Model.search(domain_base + [("name", "=ilike", model_name)], limit=1)
    if model:
        return model

    # Caso normal: modelo parcial
    model = Model.search(domain_base + [("name", "ilike", model_name)], limit=1)
    if model:
        return model

    # Si la IA mandó "Mazda 2 2026", limpiamos marca y año
    cleaned = model_name

    if brand:
        cleaned = re.sub(
            rf"\b{re.escape(brand.name)}\b",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

    cleaned = re.sub(r"\b(19|20)\d{2}\b", "", cleaned).strip()
    cleaned = clean_vehicle_text(cleaned)

    if cleaned:
        model = Model.search(domain_base + [("name", "=ilike", cleaned)], limit=1)
        if model:
            return model

        model = Model.search(domain_base + [("name", "ilike", cleaned)], limit=1)
        if model:
            return model

    return False


def find_vehicle_year(env, Lead, year_value: str | None):
    year_value = clean_vehicle_text(year_value)

    if not year_value:
        return False

    if not year_value.isdigit():
        return False

    if LEAD_YEAR_FIELD not in Lead._fields:
        return False

    field = Lead._fields[LEAD_YEAR_FIELD]

    if field.type == "integer":
        return int(year_value)

    if field.type == "char":
        return year_value

    if field.type == "many2one":
        Year = env[field.comodel_name].sudo()

        year = Year.search([("year", "=", year_value)], limit=1)
        if year:
            return year.id

    return False


def build_vehicle_lead_values(env, Lead, ai_result: dict) -> dict:
    values = {}

    vehicle_brand = clean_vehicle_text(ai_result.get("vehicle_brand"))
    vehicle_model = clean_vehicle_text(ai_result.get("vehicle_model"))
    vehicle_year = clean_vehicle_text(ai_result.get("vehicle_year"))

    _logger.info(
        "BUILD VEHICLE VALUES brand=%s model=%s year=%s ai_result=%s",
        vehicle_brand,
        vehicle_model,
        vehicle_year,
        ai_result,
    )

    brand = find_vehicle_brand(env, vehicle_brand)
    model = find_vehicle_model(env, vehicle_model, brand)
    year_value = find_vehicle_year(env, Lead, vehicle_year)

    _logger.info(
        "FOUND VEHICLE RECORDS brand=%s model=%s year_value=%s",
        brand.id if brand else False,
        model.id if model else False,
        year_value,
    )

    if brand and LEAD_BRAND_FIELD in Lead._fields:
        values[LEAD_BRAND_FIELD] = brand.id

    if model and LEAD_MODEL_FIELD in Lead._fields:
        values[LEAD_MODEL_FIELD] = model.id

    if year_value and LEAD_YEAR_FIELD in Lead._fields:
        values[LEAD_YEAR_FIELD] = year_value

    return values


def build_vehicle_info_from_ai(ai_result: dict, fallback: str = "") -> str:
    vehicle_info = (ai_result.get("vehicle_info") or "").strip()
    vehicle_brand = (ai_result.get("vehicle_brand") or "").strip()
    vehicle_model = (ai_result.get("vehicle_model") or "").strip()
    vehicle_year = str(ai_result.get("vehicle_year") or "").strip()

    if vehicle_info:
        return vehicle_info

    parts = []

    if fallback:
        parts.append(fallback)

    if vehicle_brand and vehicle_brand.lower() not in " ".join(parts).lower():
        parts.append(vehicle_brand)

    if vehicle_model and vehicle_model.lower() not in " ".join(parts).lower():
        parts.append(vehicle_model)

    if vehicle_year and vehicle_year not in " ".join(parts):
        parts.append(vehicle_year)

    return " ".join(parts).strip()
