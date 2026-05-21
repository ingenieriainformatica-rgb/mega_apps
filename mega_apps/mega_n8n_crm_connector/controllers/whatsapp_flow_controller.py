# -*- coding: utf-8 -*-

import logging

from odoo import http  # type: ignore
from odoo.http import request  # type: ignore

from ..helpers.n8n_payload_helper import get_n8n_payload
from ..helpers.whatsapp_session_helper import (
    NO_ACTIVE_SESSION_REPLY,
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

        if session.step == "advisor_handoff":
            return {
                "success": True,
                "should_use_ai": False,
                "should_send": False,
                "kind": "advisor_handoff",
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

        if next_step == "confirm_data":
            reply = get_confirmation_message(session)
            should_send = True

        return whatsapp_response(
            True,
            session.step,
            reply,
            should_send=should_send,
            session=session_snapshot(session),
        )
