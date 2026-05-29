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
    "out_of_coverage",
    "catalog_sent",
    "more_options_sent",
    "payment_link_sent",
    "battery_selected",
    "dispatch_requested",
    "advisor_handoff",
    "done",
}

MISSING_PHONE_REPLY = "No fue posible identificar tu número de WhatsApp."

NO_ACTIVE_SESSION_REPLY = (
    "No encontré una sesión activa. Escríbeme nuevamente para iniciar la atención."
)

CONFIRMATION_RETRY_REPLY = (
    "No alcancé a entender si los datos están correctos o si quieres corregir algo. "
    "Puedes decirme, por ejemplo: \"todo está bien\" o \"quiero corregir el vehículo\"."
)

RESET_SESSION_REPLY = (
    "Sin problema. Vamos a corregir la información. ¿Me regalas por favor tu nombre?"
)

TERMINAL_STEPS = {
    "out_of_coverage",
    "advisor_handoff",
    "dispatch_requested",
    "done",
}

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

WOMPI_PRIVATE_KEY_PARAM = "mega_n8n_crm_connector.wompi_private_key"
WOMPI_PRIVATE_KEY_PARAM_ALIASES = [
    WOMPI_PRIVATE_KEY_PARAM,
    "mega_n8n_crm_connector.wompi_private_key",
    "mega_n8n_crm_connector.wompi_private_key_prod",
    "mega_n8n_crm_connector.wompi_private_key_production",
    "wompi.private_key_mega",
    "wompi.private_key",
    "wompi.private_key_mega_prod",
    "wompi.private_key_mega_production",
    "wompi.private_key_prod",
    "wompi.private_key_production",
    "wompi.private_key_mega_test",
    "wompi.private_key_test",
]
WOMPI_PRIVATE_KEY_ENV_NAMES = [
    "WOMPI_PRIVATE_KEY",
    "WOMPI_PRIVATE_KEY_PROD",
    "WOMPI_PRIVATE_KEY_PRODUCTION",
    "WOMPI_PRV_KEY",
]
OLD_BATTERY_SURCHARGE = 40000
