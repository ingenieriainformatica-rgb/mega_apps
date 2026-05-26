from datetime import datetime
from textwrap import dedent
from typing import Any
import random
from .constants import (
    COLOMBIA_TZ
)


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


def get_battery_selected_message(name: str | None) -> str:
    customer = name or "señor/a"

    return (
        f"Perfecto {customer} 👍\n\n"
        "Ya registramos tu selección. Un asesor de Mega Baterías se pondrá en contacto contigo "
        "para confirmar disponibilidad, valor final y coordinar la entrega.\n\n"
        "El tiempo estimado de atención es de 30 a 45 minutos, según ubicación y disponibilidad. 🔋🚗"
    )
