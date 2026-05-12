import logging
import random
from typing import Any
from urllib.parse import parse_qs, quote, urlparse
from odoo import fields  #type: ignore

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


def _format_phone_colombia(phone: str) -> str:
    """Formatea el teléfono con prefijo +57 de Colombia"""
    if not phone:
        return ""

    # Limpiar el teléfono (solo dígitos)
    clean_phone = "".join(c for c in phone if c.isdigit())

    if not clean_phone:
        return ""

    # Si ya tiene 12 dígitos (57 + 10), solo formatear
    if len(clean_phone) == 12 and clean_phone.startswith("57"):
        return f"+{clean_phone}"

    # Si tiene 10 dígitos, agregar +57
    if len(clean_phone) == 10:
        return f"+57{clean_phone}"

    # Si ya empieza con 57 y tiene más de 10
    if clean_phone.startswith("57"):
        return f"+{clean_phone}"

    # Si no cumple ninguna condición, devolver como está
    return f"+57{clean_phone}" if clean_phone else phone

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
        # ============================================
        # 1. LIMPIAR DATOS DE ENTRADA
        # ============================================
        invoice_name = _clean(post.get("invoice_name")).upper().strip()
        phone_raw = _clean(post.get("phone")).strip()
        phone = _format_phone_colombia(phone_raw)  # ← Formatear con +57
        email = _clean(post.get("email")).strip()
        license_plate = _clean(post.get("license_plate")).upper().replace(" ", "").strip()
        website_name = _clean(post.get("website_name"))
        website_url = _clean(post.get("website_url"))
        accept_terms = post.get("accept_terms") in (True, "1", "true", "True", 1)

        # ============================================
        # 2. VALIDACIONES
        # ============================================
        if not all([invoice_name, phone, email]):
            return {"success": False, "message": "Faltan campos obligatorios."}

        if not accept_terms:
            return {"success": False, "message": "Debes aceptar términos y condiciones."}

        # ============================================
        # 3. DATOS DE CONTEXTO
        # ============================================
        client_ip = _get_client_ip()
        base_url = request.httprequest.host_url.rstrip("/")
        utm_params = _extract_all_url_params(request.httprequest, website_url)
        website = request.website

        # ============================================
        # 4. DESCRIPCIÓN DEL LEAD
        # ============================================
        description_lines = [
            "Lead creado desde modal website.",
            f"Website: {website_name}",
            f"Dominio: {base_url}",
            f"IP Cliente: {client_ip}",
            "Aceptó términos: Sí",
            "",
            f"Nombre: {invoice_name}",
            f"Teléfono: {phone}",
            f"Correo electrónico: {email}",
        ]
        if license_plate:
            description_lines.append(f"Placa: {license_plate}")

        description = "<br/>".join(description_lines)

        # ============================================
        # 5. CREAR/ACTUALIZAR PARTNER
        # ============================================
        partner = _get_or_create_partner({
            "invoice_name": invoice_name,
            "phone": phone,
            "email": email,
            "accept_terms": accept_terms,
        })

        # ============================================
        # 6. EQUIPO Y VENDEDOR SEGÚN WEBSITE
        # ============================================
        team_id = False
        user_id = False

        # Websites: 2 = megabaterias.co, 19 = nacionaldebaterias.com
        if website.id in (2, 19):
            team = request.env['crm.team'].sudo().search([
                ('name', '=', 'Baterías')
            ], limit=1)
            if team:
                team_id = team.id

            user = request.env['res.users'].sudo().search([
                ('name', '=', 'TIENDA DIGITAL')
            ], limit=1)
            if user:
                user_id = user.id

        # ============================================
        # 7. CREAR LEAD
        # ============================================
        utm_ids = utm_params['utm_ids']

        lead_vals: dict[str, Any] = {
            "name": f"Lead web - {invoice_name}",
            "partner_id": partner.id,
            "contact_name": invoice_name,
            "phone": phone,
            "mobile": phone,
            "email_from": email,
            "description": description,
            "accept_terms": accept_terms,
            "website": base_url,
            "license_plate": license_plate,
            "medium_id": utm_ids.get('medium_id') or MEDIUM_ID,
            "campaign_id": utm_ids.get('campaign_id'),
            "source_id": utm_ids.get('source_id'),
            "crm_fecha_instalacion": fields.Datetime.now(),
        }

        if team_id:
            lead_vals["team_id"] = team_id
        if user_id:
            lead_vals["user_id"] = user_id

        lead = request.env["crm.lead"].sudo().create(lead_vals)

        # ============================================
        # 8. WHATSAPP
        # ============================================
        whatsapp_data = _get_whatsapp_line()

        whatsapp_lines = [
            "Nuevo lead desde la web",
            "",
            f"Nombre: {invoice_name}",
            f"Teléfono: {phone}",
            f"Correo: {email}",
        ]
        if license_plate:
            whatsapp_lines.append(f"Placa: {license_plate}")

        # whatsapp_url = f"https://wa.me/{whatsapp_data['phone']}?text={quote('\n'.join(whatsapp_lines))}"

         # ✅ CORREGIDO: Variable separada para evitar backslash en f-string
        whatsapp_message = "\n".join(whatsapp_lines)
        whatsapp_url = f"https://wa.me/{whatsapp_data['phone']}?text={quote(whatsapp_message)}"

        # ============================================
        # 9. RESPUESTA
        # ============================================
        return {
            "success": True,
            "lead_id": lead.id,
            "partner_id": partner.id,
            "whatsapp_url": whatsapp_url,
            "message": "¡Cotización enviada! Pronto te contactaremos para coordinar la instalación de tu batería a domicilio.",
        }

    except Exception as error:
        _logger.exception("Error en get_lead_submit: %s", error)
        return {"success": False, "message": "No fue posible procesar la solicitud."}
