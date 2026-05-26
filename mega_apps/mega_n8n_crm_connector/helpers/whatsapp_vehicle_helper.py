import re
import logging
from .constants import (
    LEAD_YEAR_FIELD,
    LEAD_BRAND_FIELD,
    LEAD_MODEL_FIELD,
)

_logger = logging.getLogger(__name__)


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
