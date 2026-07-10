import logging
from typing import Any

from odoo.http import request  # type: ignore
from odoo.tools.misc import hash_sign, verify_hash_signed  # type: ignore

_logger = logging.getLogger(__name__)

SCOPE_LEAD_FORM = "mega_website_lead_demo.lead_form"
SCOPE_WHATSAPP_CLICK = "mega_website_lead_demo.whatsapp_click"

TOKEN_EXPIRATION_HOURS = 6


def generate_lead_token(scope: str) -> str:
    """Token firmado por el servidor (HMAC sobre database.secret + expiración).

    No depende de sesión ni de almacenamiento: se valida recalculando la firma,
    por lo que no puede falsificarse desde el cliente ni reutilizando el mismo
    texto fijo que antes se enviaba en `authorized_trigger`.
    """
    env = request.env(su=True)
    website_id = request.website.id if request.website else False
    return hash_sign(env, scope, {"w": website_id}, expiration_hours=TOKEN_EXPIRATION_HOURS)


def is_lead_token_valid(scope: str, token: Any) -> bool:
    if not token or not isinstance(token, str):
        return False

    env = request.env(su=True)

    try:
        return verify_hash_signed(env, scope, token) is not None
    except Exception:
        _logger.warning("Token de lead corrupto o con formato inválido. scope=%s", scope)
        return False
