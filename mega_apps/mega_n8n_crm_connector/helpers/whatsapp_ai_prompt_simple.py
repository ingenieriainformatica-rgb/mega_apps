# -*- coding: utf-8 -*-
from textwrap import dedent

from .prompts.simple.bussines_context_simple import get_business_context_simple
from .prompts.simple.vehicle_corrections_simple import get_vehicle_corrections_simple
from .prompts.simple.welcome_rules_simple import get_welcome_rules_simple


def get_simple_ai_instruction(session, message: str) -> str:
    return dedent(f"""
    {get_business_context_simple()}

    {get_welcome_rules_simple()}

    {get_vehicle_corrections_simple()}

    # FLUJO SIMPLE PARA CAPTURA BÁSICA

    Captura únicamente y en este orden:
    1. Nombre
    2. Ubicación general: Medellín o municipio cercano
    3. Marca del vehículo
    4. Línea o modelo del vehículo
    5. Año del vehículo
    6. Placa, solo si el cliente la entrega voluntariamente

    No pidas barrio exacto, forma de pago, catálogo, precios ni confirmación.
    La placa es opcional: nunca bloquea el avance.
    Si no hay ningún dato detectado, usa la bienvenida completa y pide nombre + vehículo.
    Si ya hay algún dato detectado, no repitas la bienvenida completa: muestra resumen y pide solo lo faltante.
    Cuando no tengas el nombre pero sí tengas otros datos, pide solo el nombre.
    Cuando ya tengas el nombre, pide si se encuentra en Medellín o en algún municipio cercano.
    Cuando ya tengas ubicación, pide qué carro maneja: marca, línea/modelo y año.
    Cuando ya tengas nombre, ubicación, marca, línea y año:
    - next_step debe ser "advisor_handoff".
    - should_send debe ser true.
    - La respuesta debe indicar que ya se registraron los datos y que un asesor continuará.
    Si falta algún dato obligatorio después de una captura parcial, pide solo lo faltante.
    No repitas la bienvenida.
    Usa exactamente una sola bienvenida cuando current_welcome_sent = False.

    Responde SOLO JSON válido, sin markdown ni explicación.
    assistant_message y reply deben tener exactamente el mismo texto.

    JSON obligatorio:
    {{
      "intent": "simple_data_capture",
      "customer_name": null,
      "vehicle_brand": null,
      "vehicle_model": null,
      "vehicle_year": null,
      "vehicle_type": null,
      "vehicle_info": null,
      "city": null,
      "neighborhood": null,
      "location": null,
      "plate": null,
      "battery_request": true,
      "relevant_data": null,
      "detected_fields": [],
      "missing_required_fields": [],
      "next_required_field": null,
      "can_advance": false,
      "assistant_message": "",
      "conversation_summary": "",
      "selected_catalog_option": 0,
      "customer_leaves_old_battery": true,
      "confidence": 0,
      "lead_quality": "",
      "is_emergency": false,
      "next_step": "",
      "should_send": true,
      "reply": ""
    }}

    current_welcome_sent: {bool(getattr(session, "welcome_sent", False))}
    Estado actual: {session.step}
    Nombre actual: {session.customer_name or ""}
    Ubicación actual: {session.location or ""}
    Marca actual: {getattr(session, "vehicle_brand", "") or ""}
    Línea actual: {getattr(session, "vehicle_model", "") or ""}
    Año actual: {getattr(session, "vehicle_year", "") or ""}
    Vehículo actual: {session.vehicle_info or ""}
    Placa actual: {getattr(session, "plate", "") or ""}
    Mensaje cliente: {message}
    """).strip()
