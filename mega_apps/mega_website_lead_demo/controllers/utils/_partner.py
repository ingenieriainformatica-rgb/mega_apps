import logging
from typing import Any

from odoo.http import request  # type: ignore

from ._helpers import _clean, COUNTRY_ID, STATE_ID, CITY_ID

_logger = logging.getLogger(__name__)

_IDENTIFICATION_TYPE_CC_CACHE: dict[str, int] = {}


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _get_identification_type_cc() -> Any:
    """
    Obtiene el tipo de identificación Cédula de ciudadanía.
    Se cachea por base de datos para evitar hacer la misma búsqueda
    cada vez que llega un lead desde la web.
    """
    dbname = request.env.cr.dbname
    cached_id = _IDENTIFICATION_TYPE_CC_CACHE.get(dbname)

    identification_model = request.env["l10n_latam.identification.type"].sudo()

    if cached_id:
        identification_type = identification_model.browse(cached_id)
        if identification_type.exists():
            return identification_type

    identification_type = identification_model.search([
        ("name", "=", "Cédula de ciudadanía")
    ], limit=1)

    if not identification_type:
        identification_type = identification_model.search([
            ("name", "ilike", "Cédula")
        ], limit=1)

    if identification_type:
        _IDENTIFICATION_TYPE_CC_CACHE[dbname] = identification_type.id

    return identification_type


def _find_partner_by_email(partner_model: Any, email: str) -> Any:
    """
    Busca contacto únicamente por email.
    Si el campo email_normalized existe, lo usa porque es mejor para comparar correos.
    """
    if not email:
        return partner_model.browse()

    if "email_normalized" in partner_model._fields:
        return partner_model.search([
            ("email_normalized", "=", email),
            ("is_company", "=", False),
        ], limit=1)

    return partner_model.search([
        ("email", "=", email),
        ("is_company", "=", False),
    ], limit=1)


def _get_or_create_partner(post: dict[str, Any]) -> Any:
    partner_model = request.env["res.partner"].sudo().with_context(
        tracking_disable=True,
        mail_create_nosubscribe=True,
        mail_create_nolog=True,
        mail_notrack=True,
    )

    invoice_name = _clean(post.get("invoice_name")).strip()
    phone = _clean(post.get("phone")).strip()
    email = _normalize_email(_clean(post.get("email")))
    accept_terms = bool(post.get("accept_terms"))
    website_url = _clean(post.get("website_url", "")).strip()

    # =====================================================
    # 1. Buscar contacto SOLO por email
    # =====================================================
    partner = _find_partner_by_email(partner_model, email)

    # =====================================================
    # 2. Si existe, reutilizarlo
    # =====================================================
    if partner:
        vals_update = {}

        if (
            "accept_web_terms_conditions" in partner_model._fields
            and accept_terms
            and not partner.accept_web_terms_conditions
        ):
            vals_update["accept_web_terms_conditions"] = True

        if vals_update:
            partner.write(vals_update)

        return partner

    # =====================================================
    # 3. Si no existe, crear contacto nuevo
    # =====================================================
    identification_type = _get_identification_type_cc()

    create_vals = {
        "name": invoice_name or "Cliente Web",
        "phone": phone,
        "mobile": phone,
        "email": email,
        "company_type": "person",
        "is_company": False,
        "country_id": COUNTRY_ID,
        "state_id": STATE_ID,
        "city_id": CITY_ID,
        "comment": (
            "Contacto creado desde el sitio web.<br/><br/>"
            f"Teléfono: {phone}<br/>"
            f"Email: {email}"
            + (f"<br/>URL: {website_url}" if website_url else "")
        ),
    }

    if "accept_web_terms_conditions" in partner_model._fields:
        create_vals["accept_web_terms_conditions"] = accept_terms

    if (
        identification_type
        and "l10n_latam_identification_type_id" in partner_model._fields
    ):
        create_vals["l10n_latam_identification_type_id"] = identification_type.id

    return partner_model.create(create_vals)
