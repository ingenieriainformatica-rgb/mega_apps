import logging
import random
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

from odoo.http import request  # type: ignore
from ._helpers import (
    _clean,
    _safe_int,
    _get_client_ip,
    MEDIUM_ID,
)
from ._partner import (
    _get_or_create_partner
)
from ._utm import (
    _extract_all_url_params,
)

_logger = logging.getLogger(__name__)


def _normalize_vat(value: str) -> str:
    return (value or "").replace(".", "").replace(",", "").replace(" ", "").strip()

def _get_whatsapp_line():
    website = request.website

    lines = website.sudo().lead_whatsapp_ids.filtered(lambda l: l.active)

    if not lines:
        return {
            "phone": "573508338984",
            "name": "Default",
        }

    selected = random.choice(lines)

    return {
        "phone": (selected.phone or "").replace("+", "").replace(" ", "").strip(),
        "name": selected.name,
        "user_id": selected.user_id.id if selected.user_id else False,
    }

def get_lead_brands() -> list[dict[str, Any]]:
    brand_model = request.env["fleet.vehicle.model.brand"].sudo()
    brands = brand_model.search([("show_on_website", "=", True)], order="name asc")
    return [{"id": brand.id, "name": brand.name} for brand in brands]

def get_lead_models(brand_id: Any = None) -> list[dict[str, Any]]:
    brand_id_int = _safe_int(brand_id)
    if not brand_id_int:
        return []

    model_model = request.env["fleet.vehicle.model"].sudo()
    models = model_model.search([("brand_id", "=", brand_id_int), ("show_on_website", "=", True)], order="name asc")
    return [{"id": model.id, "name": model.name} for model in models]

def get_lead_submit(post: dict[str, Any]) -> dict[str, Any]:
    try:
        invoice_name = _clean(post.get("invoice_name")).upper().strip()
        # vat = _normalize_vat(_clean(post.get("vat")))
        phone = _clean(post.get("phone")).strip()
        # street = _clean(post.get("street"))
        email = _clean(post.get("email")).strip()
        # brand_name = _clean(post.get("brand_name"))
        # model_name = _clean(post.get("model_name"))
        license_plate = _clean(post.get("license_plate")).upper().replace(" ", "").strip()
        website_name = _clean(post.get("website_name"))
        website_url = _clean(post.get("website_url"))

        # brand_id = _safe_int(post.get("brand_id"))
        # model_id = _safe_int(post.get("model_id"))

        accept_terms = post.get("accept_terms") in (True, "1", "true", "True", 1)

        if not all([invoice_name, phone, email]):
            return {
                "success": False,
                "message": "Faltan campos obligatorios.",
            }

        if not accept_terms:
            return {
                "success": False,
                "message": "Debes aceptar términos y condiciones.",
            }

        client_ip = _get_client_ip()
        base_url = request.httprequest.host_url.rstrip("/")
        utm_params = _extract_all_url_params(request.httprequest, website_url)

        description_lines = [
            "Lead creado desde modal website.",
            f"Website: {website_name}",
            f"Dominio: {base_url}",
            f"IP Cliente: {client_ip}",
            "Aceptó términos: Sí",
            "",
            f"Nombre de quien sale la factura: {invoice_name}",
            f"Teléfono: {phone}",
            f"Correo electrónico: {email}",
        ]

        # ✅ Solo agregar placa si viene
        if license_plate:
            description_lines.append(f"Placa: {license_plate}")

        description = "<br/>".join(description_lines)

        partner = _get_or_create_partner({
            "invoice_name": invoice_name,
            "phone": phone,
            "email": email,
            "accept_terms": accept_terms
        })

        utm_ids = utm_params['utm_ids']

        lead_model = request.env["crm.lead"].sudo()
        lead_vals: dict[str, Any] = {
            "name": f"Lead web - {invoice_name}",
            "partner_id": partner.id,
            "contact_name": invoice_name,
            "phone": phone,
            "mobile": phone,
            "email_from": email,
            # "street": street,
            "description": description,
            "accept_terms": accept_terms,
            "website": base_url,
            "license_plate": license_plate,
            # ✅ UTMs procesados - Si tiene valor lo usa, si no pone False o nada
            "medium_id": utm_ids.get('medium_id') or MEDIUM_ID,  # Si no hay UTM, usa el default
            "campaign_id": utm_ids.get('campaign_id'),            # Puede ser False si no vino
            "source_id": utm_ids.get('source_id'),                # Puede ser False si no vino
        }

        # if brand_id and "brand_id" in lead_model._fields:
        #     lead_vals["brand_id"] = brand_id

        # if model_id and "modelo_id" in lead_model._fields:
        #     lead_vals["modelo_id"] = model_id

        lead = lead_model.create(lead_vals)

        # whatsapp_number = "573193662738"
        whatsapp_data = _get_whatsapp_line()
        whatsapp_number = whatsapp_data["phone"]
        # advisor_name = whatsapp_data["name"]

        whatsapp_message = "\n".join([
            "Nuevo lead desde la web",
            "",
            f"Nombre: {invoice_name}",
            f"Teléfono: {phone}",
            f"Correo: {email}",
        ] + ([f"Placa: {license_plate}"] if license_plate else []))
        whatsapp_url = f"https://wa.me/{whatsapp_number}?text={quote(whatsapp_message)}"

        return {
            "success": True,
            "lead_id": lead.id,
            "partner_id": partner.id,
            "whatsapp_url": whatsapp_url,
            "message": "¡Cotización enviada! Pronto te contactaremos para coordinar la instalación de tu batería a domicilio.",
        }

    except Exception as error:
        _logger.exception("Error en get_lead_demo_submit: %s", error)
        return {
            "success": False,
            "message": "No fue posible procesar la solicitud.",
        }
