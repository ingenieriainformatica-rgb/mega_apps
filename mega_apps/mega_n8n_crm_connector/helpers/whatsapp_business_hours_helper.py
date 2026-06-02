# -*- coding: utf-8 -*-

from datetime import datetime, time

from .constants import COLOMBIA_TZ

BUSINESS_HOUR_START = time(6, 0)
BUSINESS_HOUR_END = time(19, 0)
BUSINESS_HOURS_TEXT = "lunes a sábado de 6:00 a.m. a 7:00 p.m."


def _as_colombia_datetime(now=None) -> datetime:
    current = now or datetime.now(COLOMBIA_TZ)

    if current.tzinfo is None:
        return current.replace(tzinfo=COLOMBIA_TZ)

    return current.astimezone(COLOMBIA_TZ)


def is_business_hours(now=None) -> bool:
    current = _as_colombia_datetime(now)

    # lunes=0, domingo=6
    if current.weekday() == 6:
        return False

    return BUSINESS_HOUR_START <= current.time() < BUSINESS_HOUR_END


def get_business_hours_text() -> str:
    return BUSINESS_HOURS_TEXT


def get_after_hours_message(name=None) -> str:
    greeting = f"Hola {name} 👋" if name else "Hola 👋"
    return (
        f"{greeting} Gracias por escribirnos.\n\n"
        "En este momento estamos fuera de nuestro horario de atención.\n"
        f"Nuestro horario es de {get_business_hours_text()}.\n\n"
        "Si deseas, puedes dejar tus datos y un asesor te contactará cuando retomemos atención. "
        "¿Deseas dejarlos?"
    )
