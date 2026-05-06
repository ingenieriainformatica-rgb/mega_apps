import logging
import random
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

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

def _get_identification_type_cc() -> Any:
    identification_type = request.env["l10n_latam.identification.type"].sudo().search([
        ("name", "ilike", "Cédula de ciudadanía")
    ], limit=1)

    return identification_type

def _get_or_create_partner(post: dict[str, Any]) -> Any:
    partner_model = request.env["res.partner"].sudo()

    invoice_name = _clean(post.get("invoice_name"))
    phone = _clean(post.get("phone"))
    email = _clean(post.get("email"))
    accept_terms = post.get("accept_terms")
    website_url = post.get("website_url", "")

    partner = partner_model.search([
        # ("phone", "=", phone),
        ("email", "=", email),
        ("is_company", "=", False),
    ], limit=1)

    if partner:
        vals_to_update = {}
        if not partner.accept_web_terms_conditions and accept_terms:
            vals_to_update["accept_web_terms_conditions"] = True

        if vals_to_update:
            partner.write(vals_to_update)

        return partner

    identification_type = _get_identification_type_cc()

    # Crear nuevo partner
    create_vals = {
        "name": invoice_name or "Cliente Web",
        "phone": phone,
        "mobile": phone,
        "email": email,
        "company_type": "person",
        "accept_web_terms_conditions": accept_terms,
        "is_company": False,
        "country_id": COUNTRY_ID,
        "state_id": STATE_ID,
        "city_id": CITY_ID,
    }

    # ✅ Solo asignar el ID, no el objeto completo
    if identification_type:
        create_vals["l10n_latam_identification_type_id"] = identification_type.id

    partner = partner_model.create(create_vals)

    # ✅ Mensaje en chatter cuando se crea
    message_lines = [
        "Contacto creado desde el sitio web.",
        "",
        f"Teléfono: {phone}",
        f"Email: {email}",
    ]
    if website_url:
        message_lines.append(f"🔗 URL: {website_url}")

    partner.message_post(
        body="\n".join(message_lines),
        message_type="notification",
    )

    return partner

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

def _extract_all_url_params(httprequest, website_url):
    """Extrae TODOS los parámetros de la URL automáticamente"""

    full_url = website_url
    path_url = httprequest.path

    parsed_url = urlparse(full_url)
    all_params = parse_qs(parsed_url.query)

    # ✅ Convertir listas a strings SEGURO
    clean_params = {}
    for key, value in all_params.items():
        if isinstance(value, list):
            clean_params[key] = value[0] if len(value) == 1 else value[0]
        else:
            clean_params[key] = value

    # Solo procesar si vienen los UTMs
    utm_ids = {
        'source_id': _get_or_create_utm('utm.source', clean_params.get('utm_source')),
        'medium_id': _get_or_create_utm('utm.medium', clean_params.get('utm_medium')),
        'campaign_id': _get_or_create_utm('utm.campaign', clean_params.get('utm_campaign')),
    }

    tracking_data = {
        'params': clean_params,
        'utm_ids': utm_ids,
        'full_url': full_url,
        'path_url': path_url,
        'referrer': httprequest.referrer or '',
        'user_agent': httprequest.user_agent.string or '',
        'remote_addr': httprequest.remote_addr or '',
    }

    return tracking_data

def _get_or_create_utm(model_name, value):
    """Busca o crea UTM y retorna el ID"""

    # ✅ Si es lista, tomar el primer elemento
    if isinstance(value, list):
        value = value[0] if value else None

    # ✅ Si no hay valor o está vacío
    if not value:
        return False

    # ✅ Convertir a string por si acaso
    value = str(value).strip()

    if not value:
        return False

    # Buscar si ya existe
    record = request.env[model_name].sudo().search([
        ('name', 'ilike', value)
    ], limit=1)

    if record:
        return record.id

    # Crear nuevo
    new_record = request.env[model_name].sudo().create({
        'name': value
    })

    return new_record.id
