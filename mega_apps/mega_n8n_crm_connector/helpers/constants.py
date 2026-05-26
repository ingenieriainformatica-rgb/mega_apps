# -*- coding: utf-8 -*-
# whatsapp_constants.py

from zoneinfo import ZoneInfo

COLOMBIA_TZ = ZoneInfo("America/Bogota")

CONFIRMATION_YES = {"si", "sí", "s", "correcto", "ok", "listo", "confirmo"}
CONFIRMATION_NO = {"no", "n", "incorrecto", "corregir"}

ALLOWED_STEPS = {
    "ask_name",
    "ask_vehicle",
    "ask_location",
    "confirm_data",
    "catalog_sent",
    "advisor_handoff",
    "out_of_coverage",
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

TERMINAL_STEPS = {"advisor_handoff", "done", "out_of_coverage"}

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

WHATSAPP_LINE_LABELS = {
    "1115813888271835": "Mega Baterías",
}

WHATSAPP_LINE_CONFIGS = {
    "1115813888271835": {
        "label": "Mega Baterías",
        "website": "https://megabaterias.co",
        "team_name": "Baterías",
        "user_name": "TIENDA DIGITAL",
    },
}

DEFAULT_WHATSAPP_LINE_CONFIG = {
    "label": "Mega Baterías",
    "website": "https://megabaterias.co",
    "team_name": "Baterías",
    "user_name": "TIENDA DIGITAL",
}

COVERAGE_LOCATIONS = [
    "medellin",
    "medellín",
    "bello",
    "itagui",
    "itagüí",
    "envigado",
    "sabaneta",
    "la estrella",
    "caldas",
    "copacabana",
    "girardota",
    "barbosa",
]

OUT_OF_COVERAGE_LOCATIONS = [
    "bogota",
    "bogotá",
    "cali",
    "barranquilla",
    "cartagena",
    "pereira",
    "manizales",
    "bucaramanga",
]


LEAD_BRAND_FIELD = "brand_id"
LEAD_MODEL_FIELD = "modelo_id"
LEAD_YEAR_FIELD = "year_vehicule_id"
