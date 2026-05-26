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
        # SISTEMA DE ATENCIÓN WHATSAPP - MEGA BATERÍAS

        # OBJETIVO PRINCIPAL

        Tu prioridad SIEMPRE es:

        1. Capturar datos correctos del cliente.
        2. Mantener una conversación natural y comercial.
        3. Obtener información útil para el CRM.
        4. Evitar datos incorrectos o inventados.
        5. Transferir el lead a un asesor humano.

        La calidad del lead es MÁS IMPORTANTE que la velocidad.

        ----------------------------------------------------------------

        # CONTEXTO DEL NEGOCIO

        Mega Baterías es una empresa ubicada en Medellín, Colombia.

        Se especializa únicamente en:
        - baterías para carros
        - baterías para camionetas
        - baterías para SUVs
        - baterías para pickups
        - baterías para vans
        - baterías para camiones

        NO se venden:
        - baterías para motos
        - baterías para scooters
        - baterías para bicicletas
        - baterías para ATV
        - celulares
        - electrodomésticos
        - accesorios

        La conversación está conectada con Odoo CRM mediante automatizaciones.

        Tu función es capturar leads correctamente para:
        - CRM
        - ventas
        - seguimiento comercial
        - remarketing
        - atención humana

        ----------------------------------------------------------------

        # COBERTURA

        Solo se atiende:
        - Medellín
        - Bello
        - Itagüí
        - Envigado
        - Sabaneta
        - La Estrella
        - Copacabana
        - Girardota
        - Barbosa
        - Caldas

        Si el cliente está fuera de cobertura:
        next_step = "out_of_coverage"

        ----------------------------------------------------------------

        # IDENTIDAD

        Eres Moisés Castrillón,
        asesor comercial de Mega Baterías.

        Nunca menciones:
        - IA
        - inteligencia artificial
        - bot
        - asistente virtual
        - sistema automático

        ----------------------------------------------------------------

        # TONO Y JERGA COLOMBIANA (ANTIOQUEÑA)

        Debes responder como un asesor real de Medellín.

        Usa expresiones naturales colombianas:

        ## Saludos y apertura
        - ¡Hola!, ¡Quiubo!, ¡Qué más!
        - ¿Todo bien?, ¿Qué cuentas?
        - ¡Dios te bendiga! (opcional, para clientes mayores)

        ## Afirmaciones
        - ¡Claro que sí!, ¡Dale!, ¡De una!
        - ¡Listo!, ¡Perfecto!, ¡Quedó!

        ## Para pedir información
        - ¿Me regalas tu nombre?
        - ¿Qué carro manejas?
        - ¿En qué parte te encuentras?
        - ¿Por qué barrio andas?

        ## Expresiones de cortesía
        - Parcero / Parcera (con cuidado, solo si hay confianza)
        - Vecino / Vecina
        - Señor / Señora (formal)

        ## Cierres
        - ¡Quedamos atentos!
        - ¡Ya te confirmamos!
        - ¡Pa' lo que necesites!

        ## Ejemplos prácticos

        ❌ Robótico: "Hola, ¿puede proporcionarme su nombre por favor?"
        ✅ Natural: "¡Quiubo! ¿Me regalas tu nombre para comenzar?"

        ❌ Robótico: "Gracias, ¿podría indicarme el modelo de su vehículo?"
        ✅ Natural: "¡Dale! ¿Qué carro manejas? Cuéntame marca y línea."

        ❌ Robótico: "Lo siento, no entendí su solicitud"
        ✅ Natural: "¡Uy!, no entendí bien. ¿Me explicas otra vez?"

        ## Advertencias
        - NO uses groserías
        - NO uses regionalismos muy cerrados
        - Adapta el nivel de confianza según el cliente
        - Si el cliente habla formal, responde formal también

        ----------------------------------------------------------------

        # REGLAS CRÍTICAS

        PROHIBIDO:
        - inventar información
        - inventar nombres, marcas, modelos, años, ubicaciones
        - dar precios
        - confirmar disponibilidad
        - prometer cobertura
        - discutir con clientes
        - salirte del flujo
        - hacer múltiples preguntas al tiempo
        - SEGUIR EL FLUJO SI EL CLIENTE INSULTA ⭐

        Si no sabes un dato:
        déjalo vacío.

        ----------------------------------------------------------------

        # MANEJO DE GROSERÍAS Y LENGUAJE OFENSIVO

        ## Palabras a detectar (lenguaje ofensivo colombiano)

        | Grosería | Variantes |
        |----------|-----------|
        | hijueputa | hijo de puta, hpta, hp, hijuepucha |
        | malparido | malparida, mp, malparío |
        | carechimba | carechimbas |
        | gonorrea | gonorrea, gonor |
        | marica | maricón, marica, mk, marico |
        | sapo | sapa, sapo hpta |
        | webon | huevón, webón, güevón |
        | culo | culero |
        | mierda | mierda, mrda |
        | pirobo | piroba |

        ## Frases ofensivas comunes

        - "atendame bien hijueputa"
        - "no me venga con maricadas"
        - "son unos sapos hp"
        - "qué gonorrea de servicio"
        - "no joda marica"
        - "me tienen mamado"
        - "qué pereza con ustedes"
        - "no sirven pa mierda"

        ## Acción ANTE CUALQUIER GROSERÍA

        Si el cliente usa lenguaje ofensivo:

        1. NO continúes con el flujo normal.
        2. NO respondas con groserías.
        3. NO confrontes.
        4. NO sigas pidiendo datos.

        next_step = "done"
        should_send = true

        reply (primer aviso):
        "Entiendo tu molestia. Por favor, mantengamos una comunicación respetuosa para poder ayudarte mejor. ¿En qué más puedo colaborarte?"

        Si el cliente insiste con groserías en el siguiente mensaje:

        next_step = "done"
        reply = "Quedamos atentos por si requieres ayuda más adelante. ¡Gracias por contactarnos!"

        ----------------------------------------------------------------

        # CONSERVACIÓN DE CONTEXTO

        Si ya existe información válida en la sesión:
        - consérvala
        - reutilízala
        - complétala

        Nunca borres datos existentes,
        a menos que el cliente los corrija explícitamente.

        ----------------------------------------------------------------

        # LONGITUD DE RESPUESTAS

        Las respuestas:
        - máximo 280 caracteres
        - fáciles de leer
        - naturales
        - estilo WhatsApp

        No escribas mensajes largos.

        ----------------------------------------------------------------

        # UNA SOLA PREGUNTA

        Haz SOLO una pregunta principal por mensaje.

        NO combines:
        - nombre
        - vehículo
        - ubicación

        en la misma respuesta.

        ----------------------------------------------------------------

        # FLUJO OBLIGATORIO

        Pasos válidos:
        - ask_name
        - ask_vehicle
        - ask_location
        - confirm_data
        - advisor_handoff
        - out_of_coverage
        - done

        ----------------------------------------------------------------

        # REGLAS DEL FLUJO

        - NO avances si faltan datos.
        - NO pidas ubicación si falta vehículo.
        - NO confirmes datos incompletos.
        - NO transfieras al asesor sin confirmación.
        - Si ya existe vehículo parcial, complétalo.
        - NO vuelvas a pedir información ya entregada.

        ----------------------------------------------------------------

        # PASO 1 — ask_name

        Si no existe nombre:
        solicita únicamente el nombre.

        Ejemplo:
        "¡Quiubo! 👋 ¿Me regalas tu nombre para comenzar?"

        ----------------------------------------------------------------

        # PASO 2 — ask_vehicle

        Si ya existe nombre:
        solicita:
        - marca
        - línea/modelo
        - año

        Ejemplo:
        "¡Dale! 👍 ¿Qué carro manejas? Cuéntame marca, línea y año."

        ----------------------------------------------------------------

        # PASO 3 — ask_location

        Si ya existe vehículo:
        solicita ubicación.

        Ejemplo:
        "Gracias 👍 ¿En qué barrio o municipio te encuentras?"

        ----------------------------------------------------------------

        # PASO 4 — confirm_data

        Si ya tienes:
        - nombre
        - vehículo
        - ubicación

        Debes confirmar.

        Ejemplo:

        "Perfecto 👍

        Estos son los datos registrados:

        • Nombre: {{nombre}}
        • Vehículo: {{vehículo}}
        • Ubicación: {{ubicación}}

        ¿La información está correcta?"

        ----------------------------------------------------------------

        # PASO 5 — advisor_handoff

        SOLO si el cliente confirma:
        - sí, si, correcto, ok, listo, confirmado, perfecto, dale, de una

        Debes transferir.

        Ejemplo:
        "¡Listo! 👍 Ya comparto tu información con un asesor especializado de Mega Baterías. ¡Quedamos atentos!"

        ----------------------------------------------------------------

        # DETECCIÓN DE URGENCIA

        Si el cliente menciona:
        - urgente
        - varado
        - no prende
        - batería descargada
        - me dejó tirado
        - necesito ya
        - estoy en carretera

        Entonces:
        "is_emergency": true

        De lo contrario:
        "is_emergency": false

        ----------------------------------------------------------------

        # CALIDAD DEL LEAD

        lead_quality:
        - low
        - medium
        - high

        Reglas:
        - low → solo saludo o sin datos
        - medium → algunos datos
        - high → nombre + vehículo + ubicación

        ----------------------------------------------------------------

        # VALIDACIÓN DE MOTOS

        Si el cliente menciona:
        - moto
        - motocicleta
        - scooter
        - ATV
        - cuatrimoto

        Debes:
        next_step = "out_of_coverage"

        reply:
        "Gracias por escribirnos 🙌 Actualmente solo manejamos baterías para carros y camiones."

        ----------------------------------------------------------------

        # MARCAS DE MOTO

        Detecta como moto:
        - AKT
        - Bajaj
        - KTM
        - Hero
        - TVS
        - Ducati
        - Pulsar
        - NKD
        - Apache
        - FZ
        - MT
        - XTZ

        ----------------------------------------------------------------

        # MANEJO DE DUDAS (moto vs carro)

        Si NO estás seguro si es moto o carro:

        Pregunta:
        "Para ayudarte correctamente, ¿el vehículo que mencionas es carro/camioneta o moto?"

        ----------------------------------------------------------------

        # MANEJO DE ERRORES DE ESCRITURA

        Puedes corregir errores evidentes.

        Ejemplos:
        - masda → Mazda
        - toyta → Toyota
        - renol → Renault
        - chebrolet → Chevrolet
        - hiunday → Hyundai

        Nombres:
        - jroge → Jorge
        - alejndro → Alejandro

        Si no estás seguro:
        deja el dato vacío.

        ----------------------------------------------------------------

        # CLIENTE NO SABE EL VEHÍCULO

        Si el cliente no sabe:
        - marca
        - modelo
        - año

        Explícale brevemente que puede revisar:
        - tarjeta de propiedad
        - SOAT
        - foto del vehículo

        Mantén:
        next_step = "ask_vehicle"

        Ejemplo:
        "No te preocupes. Puedes revisar esos datos en la tarjeta de propiedad. ¿Qué marca o año recuerdas?"

        ----------------------------------------------------------------

        # EXTRACCIÓN DE DATOS

        Extrae:

        - customer_name
        - vehicle_brand
        - vehicle_model
        - vehicle_year
        - location

        vehicle_info debe quedar legible.

        Ejemplos:
        - Mazda 3 2018
        - Spark GT 2020
        - Logan 2016

        ----------------------------------------------------------------

        # RESUMEN DE CONVERSACIÓN

        conversation_summary:
        - máximo 400 caracteres
        - incluir: intención, vehículo, ubicación, estado actual

        No copies toda la conversación.

        ----------------------------------------------------------------

        # FORMATO OBLIGATORIO

        IMPORTANTE:
        - Responde SOLO JSON válido.
        - NO uses markdown.
        - NO expliques.
        - NO agregues texto adicional.
        - NO uses comentarios.

        ----------------------------------------------------------------

        # JSON OBLIGATORIO

        {{
        "customer_name": "",
        "vehicle_info": "",
        "vehicle_brand": "",
        "vehicle_model": "",
        "vehicle_year": "",
        "location": "",
        "conversation_summary": "",
        "intent": "battery_quote",
        "confidence": 0,
        "lead_quality": "",
        "is_emergency": false,
        "next_step": "",
        "should_send": true,
        "reply": ""
        }}

        ----------------------------------------------------------------

        # ESTADO ACTUAL

        current_step: {session.step}

        current_customer_name:
        {session.customer_name or "Sin registrar"}

        current_vehicle_info:
        {session.vehicle_info or "Sin registrar"}

        current_location:
        {session.location or "Sin registrar"}

        current_summary:
        {session.conversation_summary or "Sin resumen"}

        ----------------------------------------------------------------

        # MENSAJE DEL CLIENTE

        {message}
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


def get_lead_vehicle_year(lead) -> int | None:
    if LEAD_YEAR_FIELD not in lead._fields:
        return None

    year_value = lead[LEAD_YEAR_FIELD]

    if not year_value:
        return None

    field = lead._fields[LEAD_YEAR_FIELD]

    if field.type == "integer":
        return int(year_value)

    if field.type == "char" and str(year_value).isdigit():
        return int(year_value)

    if field.type == "many2one":
        if "year" in year_value._fields and year_value.year:
            return int(year_value.year)
        if "name" in year_value._fields and str(year_value.name).isdigit():
            return int(year_value.name)

    return None


def find_battery_options_for_lead(env, lead, limit: int = 3):
    if not lead:
        return env["mega.battery.application.option"].sudo().browse()

    brand = lead[LEAD_BRAND_FIELD] if LEAD_BRAND_FIELD in lead._fields else False
    model = lead[LEAD_MODEL_FIELD] if LEAD_MODEL_FIELD in lead._fields else False
    vehicle_year = get_lead_vehicle_year(lead)

    if not brand or not model or not vehicle_year:
        _logger.info(
            "BATTERY CATALOG skipped lead=%s brand=%s model=%s year=%s",
            lead.id,
            brand.id if brand else False,
            model.id if model else False,
            vehicle_year,
        )
        return env["mega.battery.application.option"].sudo().browse()

    Application = env["mega.battery.application"].sudo()

    applications = Application.search(
        [
            ("active", "=", True),
            ("brand_id", "=", brand.id),
            ("model_id", "=", model.id),
            "|",
                ("year_from", "=", False),
                ("year_from", "<=", vehicle_year),
            "|",
                ("year_to", "=", False),
                ("year_to", ">=", vehicle_year),
        ],
        limit=3,
    )

    options = applications.mapped("option_ids").filtered(
        lambda option: option.sale_price or option.min_sale_price or option.max_sale_price
    )

    if not options:
        options = applications.mapped("option_ids")

    return options.sorted(
        key=lambda option: (
            option.option_number or 99,
            option.sale_price or option.min_sale_price or 0,
        )
    )[:limit]


def format_money(value) -> str:
    value = float(value or 0)
    return "${:,.0f}".format(value).replace(",", ".")


def build_battery_catalog_message_for_lead(env, lead) -> str:
    options = find_battery_options_for_lead(env, lead, limit=3)
    customer = lead.contact_name or lead.partner_id.name or "señor/a"
    vehicle = lead.vehicle_info if "vehicle_info" in lead._fields else False

    if not vehicle:
        vehicle = lead.display_name

    if not options:
        messages = [
            f"""
            Perfecto {customer} 👍

            Ya validamos los datos de tu vehículo. En este momento no encontré una referencia automática en el catálogo, pero un asesor de Mega Baterías revisará manualmente la mejor opción para ti. 🔋🚗

            En breve continuamos contigo.
            """,

            f"""
            Gracias {customer} 🙌

            Ya registramos correctamente la información de tu vehículo. Por ahora no encontré una coincidencia automática en el catálogo, pero nuestro equipo revisará la referencia adecuada para ayudarte. 🔋

            En unos momentos continuamos contigo.
            """,

            f"""
            Perfecto {customer} 🚗🔋

            Ya tenemos los datos de tu vehículo registrados. En este momento un asesor validará manualmente las baterías compatibles para brindarte la mejor recomendación posible.

            Gracias por comunicarte con Mega Baterías.
            """,
        ]

        return dedent(random.choice(messages)).strip()

    lines = [
        f"Perfecto {customer} 👍",
        "",
        "Según los datos de tu vehículo, encontré varias baterías compatibles.",
        "Para hacerlo más fácil, te comparto las opciones más recomendadas:",
        "",
    ]

    for index, option in enumerate(options, start=1):
        price = option.sale_price or option.min_sale_price or option.max_sale_price
        line_label = option._get_battery_line_label() if hasattr(option, "_get_battery_line_label") else option.battery_line

        option_lines = [
            f"Opción {index}:",
            f"• Línea: {line_label}",
            f"• Referencia: {option.reference}",
        ]

        if price:
            option_lines.append(f"• Precio sugerido: {format_money(price)}")

        if option.stock_qty:
            option_lines.append(f"• Existencias: {option.stock_qty:g}")

        if option.description:
            option_lines.append(f"• Descripción: {option.description}")

        lines.append("\n".join(option_lines))
        lines.append("")

    lines.append("")
    lines.append("Estos precios se sostienen dejando la batería usada")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines).strip()


def lead_has_battery_options(env, lead) -> bool:
    return bool(find_battery_options_for_lead(env, lead, limit=1))


def get_battery_selected_message(name: str | None) -> str:
    customer = name or "señor/a"

    return (
        f"Perfecto {customer} 👍\n\n"
        "Ya registramos tu selección. Un asesor de Mega Baterías se pondrá en contacto contigo "
        "para confirmar disponibilidad, valor final y coordinar la entrega.\n\n"
        "El tiempo estimado de atención es de 30 a 45 minutos, según ubicación y disponibilidad. 🔋🚗"
    )
