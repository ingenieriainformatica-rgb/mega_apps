import logging
import re

from odoo import http  # type: ignore
from odoo.http import request  # type: ignore
from werkzeug.exceptions import NotFound  # type: ignore

_logger = logging.getLogger(__name__)


CONTEST_WEBSITE_ID = 1
REQUIRED_FIELDS = (
    "name",
    "vat",
    "phone",
    "email",
    "street",
    "license_plate",
    "vehicle_info",
    "service_acquired",
)
SERVICE_OPTIONS = {
    "baterias",
    "llantas",
    "mega_combo",
    "mecanica_especializada",
    "cambio_aceite",
}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class MegaJerseyContestController(http.Controller):
    def _ensure_contest_website(self):
        _logger.info(f"\n\n Id -->> {request.website.id} \n\n")
        if not request.website or request.website.id != CONTEST_WEBSITE_ID:
            raise NotFound()

    def _get_client_ip(self):
        forwarded_for = request.httprequest.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.httprequest.remote_addr or ""

    def _landing_values(self, errors=None, form=None):
        return {
            "errors": errors or [],
            "form": form or {},
        }

    @http.route("/mega-fiesta-futbol", type="http", auth="public", website=True)
    def mega_jersey_landing(self, **kwargs):
        self._ensure_contest_website()
        return request.render(
            "mega_colombia_jersey_landing.template_mega_jersey_landing",
            self._landing_values(),
        )

    @http.route(
        "/mega-fiesta-futbol/submit",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def mega_jersey_landing_submit(self, **post):
        self._ensure_contest_website()

        form = {
            field_name: (post.get(field_name) or "").strip()
            for field_name in REQUIRED_FIELDS
        }
        errors = []

        for field_name in REQUIRED_FIELDS:
            if not form[field_name]:
                errors.append("Todos los campos del formulario son obligatorios.")
                break

        if form.get("email") and not EMAIL_PATTERN.match(form["email"]):
            errors.append("Ingresa un correo electrónico válido.")

        if form.get("service_acquired") and form["service_acquired"] not in SERVICE_OPTIONS:
            errors.append("Selecciona un servicio adquirido válido.")

        accept_data_policy = post.get("accept_data_policy") == "on"
        accept_commercial_info = post.get("accept_commercial_info") == "on"

        if not accept_data_policy:
            errors.append("Debes autorizar el tratamiento de datos personales y uso de imagen.")
        if not accept_commercial_info:
            errors.append("Debes autorizar el envío de información comercial.")

        if errors:
            form.update(
                {
                    "accept_data_policy": accept_data_policy,
                    "accept_commercial_info": accept_commercial_info,
                }
            )
            return request.render(
                "mega_colombia_jersey_landing.template_mega_jersey_landing",
                self._landing_values(errors=errors, form=form),
            )

        request.env["mega.jersey.contest.participant"].sudo().create(
            {
                **form,
                "accept_data_policy": accept_data_policy,
                "accept_commercial_info": accept_commercial_info,
                "website_id": request.website.id,
                "ip_address": self._get_client_ip(),
                "user_agent": request.httprequest.headers.get("User-Agent", ""),
            }
        )

        return request.render(
            "mega_colombia_jersey_landing.template_mega_jersey_thank_you"
        )
