import logging

from odoo import http  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from odoo.http import request  # type: ignore
from werkzeug.exceptions import NotFound  # type: ignore

_logger = logging.getLogger(__name__)

REQUIRED_FIELDS = (
    "name",
    "vat",
    "phone",
    "email",
    "street",
    "license_plate",
    "vehicle_info",
)
SERVICE_OPTIONS = {
    "eventos_cambio_aceite",
    "trabajos_autorizados",
    "eventos_mega_combo",
    "revision_bateria",
}


class MegaEventosController(http.Controller):
    def _ensure_target_website(self):
        target_website = request.env.ref(
            "website.default_website", raise_if_not_found=False
        )
        if not target_website or not request.website or request.website.id != target_website.id:
            raise NotFound()

    def _get_client_ip(self):
        forwarded_for = request.httprequest.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.httprequest.remote_addr or ""

    @http.route("/mega-eventos", type="http", auth="public", website=True)
    def mega_eventos_landing(self, **kwargs):
        self._ensure_target_website()
        return request.render("mega_eventos_website.template_mega_eventos_landing")

    @http.route(
        "/mega-eventos/inscribirme",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def mega_eventos_inscribirme(self, **post):
        self._ensure_target_website()

        form = {
            field_name: (post.get(field_name) or "").strip()
            for field_name in REQUIRED_FIELDS
        }
        service_acquired = (post.get("service_acquired") or "").strip()
        accept_data_policy = bool(post.get("accept_data_policy"))

        errors = []
        for field_name in REQUIRED_FIELDS:
            if not form[field_name]:
                errors.append("Todos los campos del formulario son obligatorios.")
                break

        if service_acquired not in SERVICE_OPTIONS:
            errors.append("Selecciona un beneficio válido.")

        if not accept_data_policy:
            errors.append("Debes autorizar el tratamiento de datos personales.")

        if errors:
            return {"success": False, "errors": errors}

        Participant = request.env["mega.jersey.contest.participant"].sudo()

        try:
            participant = Participant.create(
                {
                    **form,
                    "service_acquired": service_acquired,
                    "registration_source": "mega_eventos",
                    "accept_data_policy": True,
                    "accept_commercial_info": True,
                    "website_id": request.website.id,
                    "ip_address": self._get_client_ip(),
                    "user_agent": request.httprequest.headers.get("User-Agent", ""),
                }
            )
        except ValidationError as error:
            request.env.cr.rollback()
            message = error.args[0] if error.args else "No se pudo completar la inscripción."
            return {"success": False, "errors": [message]}

        return {"success": True, "code": participant.code}
