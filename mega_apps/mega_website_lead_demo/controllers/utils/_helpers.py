import logging
from typing import Any

from odoo.http import request  # type: ignore

_logger = logging.getLogger(__name__)

COUNTRY_ID = 49  # Colombia
STATE_ID = 651  # Bogotá
CITY_ID = 1  # MEDELLÍN
MEDIUM_ID = 1  # Website


def _safe_int(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "", False) else None
    except (TypeError, ValueError):
        return None


def _clean(value: Any) -> str:
    return (value or "").strip()


def _get_client_ip() -> str:
    forwarded_for = request.httprequest.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.httprequest.remote_addr or ""


def _normalize_vat(value: str) -> str:
    return (value or "").replace(".", "").replace(",", "").replace(" ", "").strip()
