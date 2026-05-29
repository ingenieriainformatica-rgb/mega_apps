# -*- coding: utf-8 -*-
from odoo import http  # type: ignore
from odoo.http import request  # type: ignore

from ..helpers.services.whatsapp_flow_service import (
    build_ai_context_response,
    apply_ai_to_whatsapp_session,
    log_terminal_whatsapp_message,
    mark_welcome_sent_after_send,
)

class N8nWhatsappSessionController(http.Controller):

    @http.route(
        "/n8n/whatsapp/session/ai-context",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        website=False,
    )
    def n8n_whatsapp_session_ai_context(self, **post):
        return build_ai_context_response(request.env)

    @http.route(
        "/n8n/whatsapp/session/apply-ai",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        website=False,
    )
    def n8n_whatsapp_session_apply_ai(self, **post):
        return apply_ai_to_whatsapp_session(request.env)

    @http.route(
        "/n8n/whatsapp/session/mark-welcome-sent",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        website=False,
    )
    def n8n_whatsapp_session_mark_welcome_sent(self, **post):
        return mark_welcome_sent_after_send(request.env)

    @http.route(
        "/n8n/whatsapp/session/log-message",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        website=False,
    )
    def n8n_whatsapp_session_log_message(self, **post):
        return log_terminal_whatsapp_message(request.env)
