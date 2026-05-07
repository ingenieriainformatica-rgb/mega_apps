import logging
from typing import Any

from odoo.http import request  # type: ignore

from ._helpers import _clean, COUNTRY_ID, STATE_ID, CITY_ID

_logger = logging.getLogger(__name__)


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
        ("email", "=", email),
        ("is_company", "=", False),
    ], limit=1)

    if partner:
        if not partner.accept_web_terms_conditions and accept_terms:
            partner.write({"accept_web_terms_conditions": True})
        return partner

    identification_type = _get_identification_type_cc()

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

    if identification_type:
        create_vals["l10n_latam_identification_type_id"] = identification_type.id

    partner = partner_model.create(create_vals)

    message_lines = [
        "Contacto creado desde el sitio web.",
        "",
        f"Teléfono: {phone}",
        f"Email: {email}",
    ]
    if website_url:
        message_lines.append(f"URL: {website_url}")

    partner.message_post(body="\n".join(message_lines), message_type="notification")

    return partner
