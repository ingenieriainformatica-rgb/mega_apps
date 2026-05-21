import json
import logging
from datetime import datetime
from textwrap import dedent
from typing import Any
from zoneinfo import ZoneInfo

from odoo import http  # type: ignore
from odoo.http import request  # type: ignore


_logger = logging.getLogger(__name__)

N8N_TOKEN = "MI_TOKEN_SECRETO_123"
TOKEN_PARAM = "mega_n8n_crm_connector.n8n_token"
COLOMBIA_TZ = ZoneInfo("America/Bogota")

CONFIRMATION_YES = {"si", "sí", "s", "correcto", "ok", "listo", "confirmo"}
CONFIRMATION_NO = {"no", "n", "incorrecto", "corregir"}
ALLOWED_STEPS = {
    "ask_name",
    "ask_vehicle",
    "ask_location",
    "confirm_data",
    "advisor_handoff",
    "done",
}

MISSING_PHONE_REPLY = "No fue posible identificar tu número de WhatsApp."
NO_ACTIVE_SESSION_REPLY = (
    "No encontré una sesión activa. Escríbeme nuevamente para iniciar la atención."
)
CONFIRMATION_RETRY_REPLY = (
    "Por favor respóndeme únicamente con Sí o No para confirmar si los datos están correctos."
)
RESET_SESSION_REPLY = (
    "Sin problema. Vamos a corregir la información. ¿Me regalas por favor tu nombre?"
)


class N8nPartnerController(http.Controller):
    def _validate_token(self, token: str | None) -> bool:
        expected_token = (
            request.env["ir.config_parameter"].sudo().get_param(TOKEN_PARAM) or N8N_TOKEN
        )
        return bool(token) and token == expected_token

    def _normalize_email(self, email: str | None) -> str:
        return (email or "").strip().lower()

    def _normalize_answer(self, message: str | None) -> str:
        return (message or "").strip().lower()

    def _get_n8n_payload(self) -> dict[str, Any]:
        payload = request.get_json_data() or {}

        if not isinstance(payload, dict):
            return {}

        params = payload.get("params")
        if isinstance(params, dict):
            return params

        return payload

    def _error_response(self, error: str, **extra: Any) -> dict[str, Any]:
        response = {"success": False, "error": error}
        response.update(extra)
        return response

    def _whatsapp_response(
        self,
        success: bool,
        step: str,
        reply: str = "",
        should_send: bool = True,
        **extra: Any,
    ) -> dict[str, Any]:
        response = {
            "success": success,
            "step": step,
            "should_send": should_send,
            "reply": reply,
        }
        response.update(extra)
        return response

    def _partner_model(self):
        return request.env["res.partner"].sudo()

    def _lead_model(self):
        return request.env["crm.lead"].sudo()

    def _session_model(self):
        return request.env["mega.whatsapp.session"].sudo()

    def _find_partner_by_email(self, email: str):
        if not email:
            return False

        return self._partner_model().search([("email", "=ilike", email)], limit=1)

    def _get_active_session(self, phone: str):
        return self._session_model().search(
            [
                ("phone", "=", phone),
                ("active", "=", True),
            ],
            limit=1,
        )

    def _create_session(self, phone: str, message: str, phone_number_id: str):
        return self._session_model().create(
            {
                "phone": phone,
                "phone_number_id": phone_number_id,
                "step": "ask_name",
                "last_message": message,
            }
        )

    def _write_last_message(self, session, message: str, phone_number_id: str) -> None:
        session.write(
            {
                "last_message": message,
                "phone_number_id": phone_number_id or session.phone_number_id,
            }
        )

    def _get_or_create_session(self, phone: str, message: str, phone_number_id: str):
        session = self._get_active_session(phone)
        if session:
            self._write_last_message(session, message, phone_number_id)
            return session, False

        return self._create_session(phone, message, phone_number_id), True

    def _session_snapshot(self, session) -> dict[str, Any]:
        return {
            "id": session.id,
            "phone": session.phone,
            "customer_name": session.customer_name or "",
            "vehicle_info": session.vehicle_info or "",
            "location": session.location or "",
        }

    def _advisor_handoff_reply(self, name: str | None) -> str:
        return (
            f"Excelente {name or 'señor/a'}, ya tengo tus datos confirmados. "
            "En breve un asesor de Mega continuará contigo para recomendarte la mejor batería. 🔋🚗"
        )

    def _missing_phone_response(self, **extra: Any) -> dict[str, Any]:
        return self._whatsapp_response(
            False,
            "error",
            MISSING_PHONE_REPLY,
            should_send=True,
            **extra,
        )

    @http.route(
        "/n8n/partner/check-email",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def check_partner_email(self, **post):
        if not self._validate_token(post.get("token")):
            return self._error_response("Token inválido", exists=False)

        email = self._normalize_email(post.get("email"))
        if not email:
            return self._error_response("Email requerido", exists=False)

        partner = self._find_partner_by_email(email)

        return {
            "success": True,
            "exists": bool(partner),
            "partner_id": partner.id if partner else False,
            "partner_name": partner.name if partner else False,
            "partner_email": partner.email if partner else email,
        }

    @http.route(
        "/n8n/crm/create-lead",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def create_lead_from_n8n(self, **post):
        if not self._validate_token(post.get("token")):
            return self._error_response("Token inválido")

        name = (post.get("name") or "Lead desde n8n").strip()
        email = self._normalize_email(post.get("email"))
        phone = (post.get("phone") or "").strip()
        contact_name = (post.get("contact_name") or name or "Cliente n8n").strip()

        partner = self._find_partner_by_email(email)
        if not partner:
            partner = self._partner_model().create(
                {
                    "name": contact_name,
                    "email": email or False,
                    "phone": phone or False,
                    "mobile": phone or False,
                    "customer_rank": 1,
                }
            )

        lead = self._lead_model().create(
            {
                "name": name,
                "partner_id": partner.id,
                "contact_name": contact_name,
                "email_from": email or partner.email,
                "phone": phone or partner.phone or partner.mobile,
                "type": "opportunity",
                "description": post.get("description") or "Lead creado desde n8n.",
            }
        )

        return {
            "success": True,
            "partner_id": partner.id,
            "partner_name": partner.name,
            "lead_id": lead.id,
            "lead_name": lead.name,
        }

    @http.route(
        "/n8n/whatsapp/session/process",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        website=False,
    )
    def n8n_whatsapp_session_process(self, **post):
        payload = self._get_n8n_payload()
        phone = (payload.get("phone") or "").strip()
        message = (payload.get("message") or "").strip()
        phone_number_id = (payload.get("phone_number_id") or "").strip()

        _logger.info("N8N WhatsApp session process phone=%s", phone)

        if not phone:
            return self._missing_phone_response()

        session, created = self._get_or_create_session(phone, message, phone_number_id)
        if created:
            return self._whatsapp_response(True, "ask_name", self._get_welcome_message())

        return self._process_manual_session_step(session, message)

    def _process_manual_session_step(self, session, message: str) -> dict[str, Any]:
        name = session.customer_name or "señor/a"

        if session.step == "ask_name":
            customer_name = self._clean_customer_name(message)
            session.write({"customer_name": customer_name, "step": "ask_vehicle"})
            return self._whatsapp_response(
                True,
                "ask_vehicle",
                f"Gracias {customer_name}. ¿Para qué vehículo necesitas la batería? 🔋🚗",
            )

        if session.step == "ask_vehicle":
            session.write({"vehicle_info": message, "step": "ask_location"})
            return self._whatsapp_response(
                True,
                "ask_location",
                f"Perfecto {name}. ¿En qué barrio o ubicación te encuentras para validar cobertura y disponibilidad?",
            )

        if session.step == "ask_location":
            session.write({"location": message, "step": "confirm_data"})
            return self._whatsapp_response(
                True,
                "confirm_data",
                self._get_confirmation_message(session),
            )

        if session.step == "confirm_data":
            return self._process_confirmation_step(session, message)

        return self._whatsapp_response(True, session.step, should_send=False)

    def _process_confirmation_step(self, session, message: str) -> dict[str, Any]:
        normalized = self._normalize_answer(message)
        name = session.customer_name or "señor/a"

        if normalized in CONFIRMATION_YES:
            session.write({"step": "advisor_handoff"})
            return self._whatsapp_response(
                True,
                "advisor_handoff",
                self._advisor_handoff_reply(name),
            )

        if normalized in CONFIRMATION_NO:
            session.write(
                {
                    "customer_name": False,
                    "vehicle_info": False,
                    "location": False,
                    "step": "ask_name",
                }
            )
            return self._whatsapp_response(True, "ask_name", RESET_SESSION_REPLY)

        return self._whatsapp_response(True, "confirm_data", CONFIRMATION_RETRY_REPLY)

    def _get_confirmation_message(self, session) -> str:
        name = session.customer_name or "No registrado"
        vehicle = session.vehicle_info or "No registrado"
        location = session.location or "No registrada"

        return dedent(
            f"""
            Perfecto {name}, por favor confirma si estos datos están correctos:

            Nombre: {name}
            Vehículo: {vehicle}
            Ubicación: {location}

            ¿La información es correcta? Responde Sí o No.
            """
        ).strip()

    def _clean_customer_name(self, message: str | None) -> str:
        name = (message or "").strip()
        lower_name = name.lower()

        prefixes = (
            "mi nombre es ",
            "me llamo ",
            "soy ",
            "buenos días soy ",
            "buenas tardes soy ",
            "buenas noches soy ",
        )

        for prefix in prefixes:
            if lower_name.startswith(prefix):
                name = name[len(prefix):].strip()
                break

        return name.title() or "Cliente"

    @http.route(
        "/n8n/whatsapp/session/ai-context",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        website=False,
    )
    def n8n_whatsapp_session_ai_context(self, **post):
        payload = self._get_n8n_payload()
        phone = (payload.get("phone") or "").strip()
        message = (payload.get("message") or "").strip()
        phone_number_id = (payload.get("phone_number_id") or "").strip()

        _logger.info("N8N AI context phone=%s step_payload=%s", phone, payload.get("step"))

        if not phone:
            return self._missing_phone_response(
                error="missing_phone",
                should_use_ai=False,
            )

        session, _created = self._get_or_create_session(phone, message, phone_number_id)

        if session.step == "advisor_handoff":
            return {
                "success": True,
                "should_use_ai": False,
                "should_send": False,
                "step": session.step,
                "reply": "",
            }

        return {
            "success": True,
            "should_use_ai": True,
            "should_send": False,
            "phone": session.phone,
            "phone_number_id": session.phone_number_id,
            "step": session.step,
            "customer_name": session.customer_name or "",
            "vehicle_info": session.vehicle_info or "",
            "location": session.location or "",
            "last_message": message,
            "ai_instruction": self._get_ai_instruction(session, message),
        }

    def _get_ai_instruction(self, session, message: str) -> str:
        return dedent(
            f"""
            Eres un asesor virtual de Mega Baterías en Medellín.

            Tu tarea es interpretar el mensaje del cliente y ayudar a capturar datos para cotizar una batería de vehículo.

            Debes devolver SOLO JSON válido con esta estructura:

            {{
              "customer_name": "",
              "vehicle_info": "",
              "location": "",
              "intent": "",
              "confidence": 0,
              "next_step": "",
              "should_send": true,
              "reply": ""
            }}

            Reglas:
            - No inventes datos.
            - Si el cliente da nombre, extrae customer_name.
            - Si menciona marca, modelo, línea o año del vehículo, extrae vehicle_info.
            - Si menciona barrio, ciudad o ubicación, extrae location.
            - Si busca batería, intent debe ser "battery_quote".
            - Si falta nombre, next_step debe ser "ask_name".
            - Si next_step es "ask_name", el campo reply debe ser EXACTAMENTE este texto:

            {self._get_welcome_message()}

            - Si falta vehículo, next_step debe ser "ask_vehicle".
            - Si falta ubicación, next_step debe ser "ask_location".
            - Si están nombre, vehículo y ubicación, next_step debe ser "confirm_data".
            - Si el cliente confirma los datos con sí, ok, correcto o listo, next_step debe ser "advisor_handoff".
            - Si el cliente pide asesor humano, next_step debe ser "advisor_handoff".
            - No des precios.
            - No confirmes disponibilidad.
            - Responde corto y natural para WhatsApp.
            - Devuelve únicamente JSON válido, sin markdown, sin explicación y sin texto adicional.

            Estado actual: {session.step}
            Nombre actual: {session.customer_name or ""}
            Vehículo actual: {session.vehicle_info or ""}
            Ubicación actual: {session.location or ""}
            Mensaje del cliente: {message}
            """
        ).strip()

    @http.route(
        "/n8n/whatsapp/session/apply-ai",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        website=False,
    )
    def n8n_whatsapp_session_apply_ai(self, **post):
        payload = self._get_n8n_payload()
        phone = (payload.get("phone") or "").strip()
        ai_result = self._parse_ai_result(payload.get("ai_result"))

        _logger.info("N8N WhatsApp apply AI phone=%s", phone)

        if not phone:
            return self._missing_phone_response()

        session = self._get_active_session(phone)
        if not session:
            return self._whatsapp_response(False, "error", NO_ACTIVE_SESSION_REPLY)

        if session.step == "advisor_handoff":
            return self._whatsapp_response(True, session.step, should_send=False)

        next_step, should_send, reply, vals = self._build_ai_session_update(
            session,
            ai_result,
        )
        session.write(vals)

        if next_step == "confirm_data":
            reply = self._get_confirmation_message(session)
            should_send = True

        return self._whatsapp_response(
            True,
            session.step,
            reply,
            should_send=should_send,
            session=self._session_snapshot(session),
        )

    def _parse_ai_result(self, ai_result: Any) -> dict[str, Any]:
        if isinstance(ai_result, dict):
            return ai_result

        if isinstance(ai_result, str):
            try:
                parsed = json.loads(ai_result)
            except json.JSONDecodeError:
                _logger.warning("Invalid AI JSON result: %s", ai_result)
                return {}

            return parsed if isinstance(parsed, dict) else {}

        return {}

    def _build_ai_session_update(
        self,
        session,
        ai_result: dict[str, Any],
    ) -> tuple[str, bool, str, dict[str, Any]]:
        customer_name = (ai_result.get("customer_name") or "").strip()
        vehicle_info = (ai_result.get("vehicle_info") or "").strip()
        location = (ai_result.get("location") or "").strip()
        next_step = (ai_result.get("next_step") or session.step).strip()
        reply = (ai_result.get("reply") or "").strip()
        should_send = bool(ai_result.get("should_send", True))

        if next_step not in ALLOWED_STEPS:
            next_step = session.step

        current_name = customer_name or session.customer_name or ""
        current_vehicle = vehicle_info or session.vehicle_info or ""
        current_location = location or session.location or ""
        normalized_message = self._normalize_answer(session.last_message)

        if session.step == "confirm_data":
            next_step, should_send, reply, current_name, current_vehicle, current_location = (
                self._resolve_confirmation_from_ai(
                    normalized_message,
                    current_name,
                    current_vehicle,
                    current_location,
                )
            )
        elif not current_name:
            next_step = "ask_name"
            should_send = True
            reply = reply or "Con gusto te ayudo. ¿Me regalas por favor tu nombre?"
        elif not current_vehicle:
            next_step = "ask_vehicle"
            should_send = True
            reply = reply or f"Gracias {current_name}. ¿Para qué vehículo necesitas la batería? 🔋🚗"
        elif not current_location:
            next_step = "ask_location"
            should_send = True
            reply = reply or (
                f"Perfecto {current_name}. ¿En qué barrio o ubicación te encuentras "
                "para validar cobertura y disponibilidad?"
            )
        elif next_step not in {"confirm_data", "advisor_handoff"}:
            next_step = "confirm_data"
            should_send = True

        vals = self._build_session_vals(
            next_step,
            current_name,
            current_vehicle,
            current_location,
        )
        return next_step, should_send, reply, vals

    def _resolve_confirmation_from_ai(
        self,
        normalized_message: str,
        current_name: str,
        current_vehicle: str,
        current_location: str,
    ) -> tuple[str, bool, str, str, str, str]:
        if normalized_message in CONFIRMATION_YES:
            return (
                "advisor_handoff",
                True,
                self._advisor_handoff_reply(current_name),
                current_name,
                current_vehicle,
                current_location,
            )

        if normalized_message in CONFIRMATION_NO:
            return "ask_name", True, RESET_SESSION_REPLY, "", "", ""

        return (
            "confirm_data",
            True,
            CONFIRMATION_RETRY_REPLY,
            current_name,
            current_vehicle,
            current_location,
        )

    def _build_session_vals(
        self,
        next_step: str,
        current_name: str,
        current_vehicle: str,
        current_location: str,
    ) -> dict[str, Any]:
        vals: dict[str, Any] = {"step": next_step}

        if current_name:
            vals["customer_name"] = current_name
        if current_vehicle:
            vals["vehicle_info"] = current_vehicle
        if current_location:
            vals["location"] = current_location

        if next_step == "ask_name":
            vals.update(
                {
                    "customer_name": False,
                    "vehicle_info": False,
                    "location": False,
                }
            )

        return vals

    def _get_colombia_greeting(self) -> str:
        hour = datetime.now(COLOMBIA_TZ).hour

        if 5 <= hour < 12:
            return "buenos días"
        if 12 <= hour < 19:
            return "buenas tardes"
        return "buenas noches"

    def _get_welcome_message(self) -> str:
        return dedent(
            f"""
            Hola, muy {self._get_colombia_greeting()}. Un gusto saludarte.
            Te habla Moisés Castrillón, asesor de Mega Baterías. 🔋🚗

            ¿Me regalas por favor tu nombre?
            Y cuéntame, ¿qué tipo de batería estás buscando y para qué vehículo la necesitas?

            Estoy atento para asesorarte y recomendarte la mejor opción según tu vehículo y presupuesto. 👍
            """
        ).strip()
