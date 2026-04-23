import logging
from typing import Any
from urllib.parse import quote

from odoo.http import request  # type: ignore

_logger = logging.getLogger(__name__)


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
    vat = _normalize_vat(_clean(post.get("vat")))
    phone = _clean(post.get("phone"))
    street = _clean(post.get("street"))
    email = _clean(post.get("email"))

    identification_type = _get_identification_type_cc()

    partner = partner_model.search(
        [("vat", "=", vat), ("is_company", "=", False)],
        limit=1
    )

    if partner:
        vals_to_update = {}

        if not partner.name and invoice_name:
            vals_to_update["name"] = invoice_name
        if not partner.phone and phone:
            vals_to_update["phone"] = phone
        if not partner.mobile and phone:
            vals_to_update["mobile"] = phone
        if not partner.email and email:
            vals_to_update["email"] = email
        if not partner.street and street:
            vals_to_update["street"] = street
        if not partner.l10n_latam_identification_type_id and identification_type:
            vals_to_update["l10n_latam_identification_type_id"] = identification_type.id

        if vals_to_update:
            partner.write(vals_to_update)

        return partner

    create_vals = {
        "name": invoice_name,
        "vat": vat,
        "phone": phone,
        "mobile": phone,
        "email": email,
        "street": street,
        "company_type": "person",
        "is_company": False,
    }

    if identification_type:
        create_vals["l10n_latam_identification_type_id"] = identification_type.id

    return partner_model.create(create_vals)

def get_lead_brands() -> list[dict[str, Any]]:
    brand_model = request.env["fleet.vehicle.model.brand"].sudo()
    brands = brand_model.search([], order="name asc")
    return [{"id": brand.id, "name": brand.name} for brand in brands]

def get_lead_models(brand_id: Any = None) -> list[dict[str, Any]]:
    brand_id_int = _safe_int(brand_id)
    if not brand_id_int:
        return []

    model_model = request.env["fleet.vehicle.model"].sudo()
    models = model_model.search([("brand_id", "=", brand_id_int)], order="name asc")
    return [{"id": model.id, "name": model.name} for model in models]

def get_lead_submit(post: dict[str, Any]) -> dict[str, Any]:
    try:
        _logger.info("Lead demo submit called with post: %s", post)

        invoice_name = _clean(post.get("invoice_name"))
        vat = _normalize_vat(_clean(post.get("vat")))
        phone = _clean(post.get("phone"))
        street = _clean(post.get("street"))
        email = _clean(post.get("email"))
        brand_name = _clean(post.get("brand_name"))
        model_name = _clean(post.get("model_name"))
        license_plate = _clean(post.get("license_plate")).upper().replace(" ", "")
        website_name = _clean(post.get("website_name"))

        brand_id = _safe_int(post.get("brand_id"))
        model_id = _safe_int(post.get("model_id"))

        accept_terms = post.get("accept_terms") in (True, "1", "true", "True", 1)

        if not all([invoice_name, vat, phone, email, license_plate]):
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

        description_lines = [
            "Lead creado desde modal website.",
            f"Website: {website_name}",
            f"Dominio: {base_url}",
            f"IP Cliente: {client_ip}",
            "Aceptó términos: Sí",
            "",
            f"Nombre de quien sale la factura: {invoice_name}",
            f"Cédula o NIT: {vat}",
            f"Teléfono: {phone}",
            f"Dirección: {street}",
            f"Correo electrónico: {email}",
            f"Marca: {brand_name}",
            f"Modelo: {model_name}",
            f"Placa: {license_plate}",
        ]
        description = "<br/>".join(description_lines)

        partner = _get_or_create_partner({
            "invoice_name": invoice_name,
            "vat": vat,
            "phone": phone,
            "street": street,
            "email": email,
        })

        lead_model = request.env["crm.lead"].sudo()
        lead_vals: dict[str, Any] = {
            "name": f"Lead web - {invoice_name}",
            "partner_id": partner.id,
            "contact_name": invoice_name,
            "phone": phone,
            "mobile": phone,
            "email_from": email,
            "street": street,
            "description": description,
            "accept_terms": accept_terms,
            "website": base_url,
            "license_plate": license_plate,
        }

        if brand_id and "brand_id" in lead_model._fields:
            lead_vals["brand_id"] = brand_id

        if model_id and "modelo_id" in lead_model._fields:
            lead_vals["modelo_id"] = model_id

        lead = lead_model.create(lead_vals)

        whatsapp_number = "573193662738"
        whatsapp_message = "\n".join([
            "Nuevo lead desde la web",
            "",
            f"Nombre: {invoice_name}",
            f"Cédula/NIT: {vat}",
            f"Teléfono: {phone}",
            f"Dirección: {street}",
            f"Correo: {email}",
            f"Placa: {license_plate}",
            f"Marca: {brand_name}",
            f"Modelo: {model_name}",
        ])
        whatsapp_url = f"https://wa.me/{whatsapp_number}?text={quote(whatsapp_message)}"

        return {
            "success": True,
            "lead_id": lead.id,
            "partner_id": partner.id,
            "whatsapp_url": whatsapp_url,
        }

    except Exception as error:
        _logger.exception("Error en get_lead_demo_submit: %s", error)
        return {
            "success": False,
            "message": "No fue posible procesar la solicitud.",
        }
