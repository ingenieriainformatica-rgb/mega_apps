import logging

from odoo import http  # type: ignore
from odoo.http import request  # type: ignore
from werkzeug.exceptions import NotFound  # type: ignore

_logger = logging.getLogger(__name__)


class MegaEventosController(http.Controller):
    def _ensure_target_website(self):
        target_website = request.env.ref(
            "website.default_website", raise_if_not_found=False
        )
        if not target_website or not request.website or request.website.id != target_website.id:
            raise NotFound()

    @http.route("/mega-eventos", type="http", auth="public", website=True)
    def mega_eventos_landing(self, **kwargs):
        self._ensure_target_website()
        return request.render("mega_eventos_website.template_mega_eventos_landing")
