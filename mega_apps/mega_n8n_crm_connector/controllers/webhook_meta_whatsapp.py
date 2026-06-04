# -*- coding: utf-8 -*-

import hashlib
import json
import logging

from odoo import http  #type: ignore
from odoo.http import request, Response  #type: ignore

_logger = logging.getLogger(__name__)


class MetaWhatsAppWebhookController(http.Controller):
    """
    Webhook directo de Meta WhatsApp hacia Odoo.

    GET  -> verificación de Meta.
    POST -> recepción de eventos de WhatsApp.
    """

    def _get_verify_token(self):
        """
        Token que vas a poner también en Meta.

        Recomendado:
        Guardarlo luego en Ajustes > Técnico > Parámetros del sistema:
        mega_n8n_crm_connector.meta_verify_token

        Mientras pruebas, puedes dejar el fallback temporal.
        """
        return request.env["ir.config_parameter"].sudo().get_param(
            "mega_n8n_crm_connector.meta_verify_token",
            "CAMBIA_ESTE_TOKEN_TEMPORAL",
        )

    def _json_response(self, data, status=200):
        return Response(
            json.dumps(data),
            status=status,
            content_type="application/json",
        )

    @http.route(
        "/webhook/meta/whatsapp",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        website=False,
    )
    def meta_whatsapp_verify(self, **kwargs):
        """
        Verificación inicial que hace Meta cuando das clic en
        'Verificar y guardar'.
        """
        mode = request.params.get("hub.mode")
        token = request.params.get("hub.verify_token")
        challenge = request.params.get("hub.challenge")

        expected_token = self._get_verify_token()

        _logger.info(
            "[META WHATSAPP VERIFY] mode=%s token_ok=%s challenge_present=%s",
            mode,
            token == expected_token,
            bool(challenge),
        )

        if mode == "subscribe" and token == expected_token and challenge:
            return Response(
                challenge,
                status=200,
                content_type="text/plain",
            )

        return Response(
            "Forbidden",
            status=403,
            content_type="text/plain",
        )

    @http.route(
        "/webhook/meta/whatsapp",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        website=False,
    )
    def meta_whatsapp_webhook(self, **kwargs):
        """
        Recepción real de eventos Meta WhatsApp.

        Por ahora:
        - recibe el payload
        - ignora estados
        - extrae mensajes entrantes
        - deja logs
        - responde OK

        Luego aquí se conecta la lógica existente que crea sesión,
        canal Discuss y mail.message.
        """
        raw_body = request.httprequest.get_data(as_text=True) or "{}"
        payload_hash = hashlib.sha256(raw_body.encode("utf-8")).hexdigest()[:16]

        try:
            payload = json.loads(raw_body)
        except Exception:
            _logger.exception(
                "[META WHATSAPP WEBHOOK] Payload JSON inválido hash=%s",
                payload_hash,
            )
            return self._json_response({"success": False, "error": "invalid_json"}, status=400)

        messages = self._extract_inbound_messages(payload)

        if not messages:
            _logger.info(
                "[META WHATSAPP WEBHOOK] Evento recibido sin mensajes entrantes. hash=%s",
                payload_hash,
            )
            return self._json_response({"success": True, "ignored": True})

        for msg in messages:
            _logger.info(
                "[META WHATSAPP WEBHOOK] Mensaje entrante recibido phone=%s wamid=%s type=%s text=%s hash=%s",
                msg.get("phone"),
                msg.get("external_message_id"),
                msg.get("message_type"),
                msg.get("text"),
                payload_hash,
            )

            # IMPORTANTE:
            # Aquí NO creamos todavía el mensaje dos veces.
            # Aquí después conectas tu lógica existente del módulo:
            #
            # request.env["TU.MODELO"].sudo()._process_inbound_meta_message(
            #     phone=msg["phone"],
            #     message=msg["text"],
            #     external_message_id=msg["external_message_id"],
            #     payload=payload,
            # )
            #
            # Pero primero prueba que Meta ya entra correctamente a Odoo.

        return self._json_response(
            {
                "success": True,
                "processed_messages": len(messages),
            }
        )

    def _extract_inbound_messages(self, payload):
        """
        Extrae únicamente mensajes entrantes reales.

        Ignora:
        - statuses
        - delivered
        - read
        - sent
        - eventos que no tengan messages
        """
        result = []

        entries = payload.get("entry") or []
        for entry in entries:
            changes = entry.get("changes") or []

            for change in changes:
                value = change.get("value") or {}

                messages = value.get("messages") or []
                if not messages:
                    continue

                contacts = value.get("contacts") or []
                contact_by_wa_id = {
                    contact.get("wa_id"): contact
                    for contact in contacts
                    if contact.get("wa_id")
                }

                for message in messages:
                    phone = message.get("from")
                    external_message_id = message.get("id")
                    message_type = message.get("type")
                    text = self._extract_message_text(message)

                    contact = contact_by_wa_id.get(phone) or {}
                    profile = contact.get("profile") or {}
                    contact_name = profile.get("name")

                    if not phone or not external_message_id:
                        _logger.warning(
                            "[META WHATSAPP WEBHOOK] Mensaje ignorado por falta de phone o wamid. phone=%s wamid=%s",
                            phone,
                            external_message_id,
                        )
                        continue

                    result.append(
                        {
                            "phone": phone,
                            "contact_name": contact_name,
                            "external_message_id": external_message_id,
                            "message_type": message_type,
                            "text": text,
                            "raw_message": message,
                        }
                    )

        return result

    def _extract_message_text(self, message):
        """
        Obtiene texto visible según el tipo de mensaje.
        """
        message_type = message.get("type")

        if message_type == "text":
            return (message.get("text") or {}).get("body") or ""

        if message_type == "button":
            return (message.get("button") or {}).get("text") or ""

        if message_type == "interactive":
            interactive = message.get("interactive") or {}

            button_reply = interactive.get("button_reply") or {}
            if button_reply:
                return button_reply.get("title") or button_reply.get("id") or ""

            list_reply = interactive.get("list_reply") or {}
            if list_reply:
                return list_reply.get("title") or list_reply.get("id") or ""

        if message_type == "image":
            return (message.get("image") or {}).get("caption") or "[Imagen recibida]"

        if message_type == "audio":
            return "[Audio recibido]"

        if message_type == "document":
            document = message.get("document") or {}
            filename = document.get("filename") or "documento"
            return "[Documento recibido: %s]" % filename

        return "[Mensaje WhatsApp tipo %s]" % (message_type or "desconocido")
