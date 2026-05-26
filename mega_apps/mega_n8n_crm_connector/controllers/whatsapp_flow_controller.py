# -*- coding: utf-8 -*-

import logging

from odoo import http  # type: ignore
from odoo.http import request  # type: ignore

from ..helpers.n8n_payload_helper import get_n8n_payload
from ..helpers.constants import NO_ACTIVE_SESSION_REPLY
from ..helpers.whatsapp_session_helper import (
    build_ai_session_update,
    get_active_session,
    get_ai_instruction,
    get_confirmation_message,
    get_or_create_session,
    missing_phone_response,
    parse_ai_result,
    session_snapshot,
    whatsapp_response,
    get_welcome_message,
    is_terminal_step,
    create_or_update_lead_from_session,
    log_whatsapp_conversation_on_lead,
    log_customer_message_on_lead_from_session,
    build_battery_catalog_message_for_lead,
    lead_has_battery_options,
)


_logger = logging.getLogger(__name__)


class N8nWhatsappSessionController(http.Controller):
    """
    Controller limpio solo para el flujo WhatsApp + IA.

    Endpoints activos:
    - /n8n/whatsapp/session/ai-context
    - /n8n/whatsapp/session/apply-ai
    """

    @http.route(
        "/n8n/whatsapp/session/ai-context",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        website=False,
    )
    def n8n_whatsapp_session_ai_context(self, **post):
        payload = get_n8n_payload()

        phone = (payload.get("phone") or "").strip()
        message = (payload.get("message") or "").strip()
        phone_number_id = (payload.get("phone_number_id") or "").strip()

        _logger.info(
            "N8N AI context phone=%s step_payload=%s",
            phone,
            payload.get("step"),
        )

        if not phone:
            return missing_phone_response(
                error="missing_phone",
                should_use_ai=False,
            )

        session, created = get_or_create_session(
            request.env,
            phone,
            message,
            phone_number_id,
        )

        if created:
            _logger.info("\n\n\n Primer mensaje debe de ser mensaje de bienvenida \n\n\n")
            return {
                "success": True,
                "should_use_ai": False,
                "should_send": True,
                "kind": "welcome",
                "phone": session.phone,
                "phone_number_id": session.phone_number_id,
                "step": session.step,
                "reply": get_welcome_message(),
                "session": session_snapshot(session),
            }

        if is_terminal_step(session.step):
            return {
                "success": True,
                "should_use_ai": False,
                "should_send": False,
                "kind": "terminal_session",
                "phone": session.phone,
                "phone_number_id": session.phone_number_id,
                "step": session.step,
                "reply": "",
                "session": session_snapshot(session),
            }

        return {
            "success": True,
            "should_use_ai": True,
            "should_send": False,
            "kind": "ai_context",
            "phone": session.phone,
            "phone_number_id": session.phone_number_id,
            "step": session.step,
            "customer_name": session.customer_name or "",
            "vehicle_info": session.vehicle_info or "",
            "location": session.location or "",
            "last_message": message,
            "ai_instruction": get_ai_instruction(session, message),
            "session": session_snapshot(session),
        }

    @http.route(
        "/n8n/whatsapp/session/apply-ai",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        website=False,
    )
    def n8n_whatsapp_session_apply_ai(self, **post):
        payload = get_n8n_payload()

        phone = (payload.get("phone") or "").strip()
        ai_result = parse_ai_result(payload.get("ai_result"))

        _logger.info("N8N WhatsApp apply AI phone=%s", phone)

        if not phone:
            return missing_phone_response()

        session = get_active_session(request.env, phone)

        if not session:
            return whatsapp_response(
                False,
                "error",
                NO_ACTIVE_SESSION_REPLY,
            )

        if session.step == "advisor_handoff":
            return whatsapp_response(
                True,
                session.step,
                should_send=False,
            )

        next_step, should_send, reply, vals = build_ai_session_update(
            session,
            ai_result,
        )

        session.write(vals)

        # lead = create_or_update_lead_from_session(request.env, session)
        lead = create_or_update_lead_from_session(
            request.env,
            session,
            ai_result=ai_result,
        )

        if next_step == "catalog_sent" and lead:
            has_options = lead_has_battery_options(request.env, lead)
            reply = build_battery_catalog_message_for_lead(request.env, lead)
            should_send = True
            if not has_options:
                session.write({"step": "advisor_handoff"})


        if next_step == "confirm_data":
            reply = get_confirmation_message(session)
            should_send = True

        if lead:
            log_whatsapp_conversation_on_lead(
                lead,
                customer_message=session.last_message,
                bot_reply=reply if should_send else "",
            )

        return whatsapp_response(
            True,
            session.step,
            reply,
            should_send=should_send,
            session=session_snapshot(session),
            lead_id=lead.id if lead else False,
        )



    @http.route(
        "/n8n/whatsapp/session/log-message",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        website=False,
    )
    def n8n_whatsapp_session_log_message(self, **post):
        payload = get_n8n_payload()

        phone = (payload.get("phone") or "").strip()
        message = (payload.get("message") or "").strip()
        message_id = (payload.get("message_id") or "").strip()

        _logger.info(
            "N8N WhatsApp log message phone=%s message_id=%s",
            phone,
            message_id,
        )

        if not phone:
            return missing_phone_response(
                error="missing_phone",
                should_use_ai=False,
                should_send=False,
            )

        session = get_active_session(request.env, phone)

        if not session:
            return whatsapp_response(
                False,
                "error",
                "No encontré una sesión activa para registrar el mensaje.",
                should_send=False,
                should_use_ai=False,
                kind="no_active_session",
            )

        # Seguridad: aunque n8n ya validó el IF, Odoo vuelve a validar.
        if not is_terminal_step(session.step):
            return whatsapp_response(
                True,
                session.step,
                "",
                should_send=False,
                should_use_ai=False,
                kind="ignored_not_terminal_session",
                session=session_snapshot(session),
            )

        # Este es el punto clave:
        # NO buscamos otro lead por teléfono.
        # El lead correcto es el vinculado a la sesión activa.
        if not session.lead_id:
            return whatsapp_response(
                False,
                session.step,
                "",
                should_send=False,
                should_use_ai=False,
                kind="session_without_lead",
                session=session_snapshot(session),
            )

        logged = log_customer_message_on_lead_from_session(
            session,
            message=message,
            message_id=message_id,
        )

        return whatsapp_response(
            True,
            session.step,
            "",
            should_send=False,
            should_use_ai=False,
            kind="message_logged" if logged else "message_not_logged",
            logged=logged,
            lead_id=session.lead_id.id,
            session=session_snapshot(session),
        )
