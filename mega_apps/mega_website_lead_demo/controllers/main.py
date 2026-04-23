import logging
from typing import Any

from odoo import http  # type: ignore

from .utils.services import (
    get_lead_brands,
    get_lead_models,
    get_lead_submit,
)  # type: ignore


_logger = logging.getLogger(__name__)


class WebsiteLeadDemoController(http.Controller):

    @http.route('/lead/brands', type='json', auth='public', website=True, csrf=False)
    def lead_brands(self) -> list[dict[str, Any]]:
        try:
            return get_lead_brands()
        except Exception as error:
            _logger.exception("Error obteniendo marcas del lead demo: %s", error)
            return []

    @http.route('/lead/models', type='json', auth='public', website=True, csrf=False)
    def lead_models(self, brand_id: Any = None) -> list[dict[str, Any]]:
        try:
            brand_id_int = int(brand_id) if brand_id else None
            return get_lead_models(brand_id_int)
        except (TypeError, ValueError):
            _logger.warning("brand_id inválido recibido en /lead_demo/models: %s", brand_id)
            return []
        except Exception as error:
            _logger.exception("Error obteniendo modelos del lead demo: %s", error)
            return []

    @http.route('/lead/submit', type='json', auth='public', website=True, csrf=False)
    def lead_submit(self, **post: Any) -> dict[str, Any]:
        try:
            return get_lead_submit(post)
        except Exception as error:
            _logger.exception("Error enviando lead demo: %s", error)
            return {
                "success": False,
                "message": "Ocurrió un error al procesar la solicitud.",
            }
