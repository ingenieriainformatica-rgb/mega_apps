# -*- coding: utf-8 -*-

import hashlib
import json
import logging
import requests

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

    def _get_n8n_webhook_url(self):
        return request.env["ir.config_parameter"].sudo().get_param(
            "mega_n8n_crm_connector.n8n_inbound_webhook_url"
        )

    def _is_debounce_enabled(self):
        value = request.env["ir.config_parameter"].sudo().get_param(
            "mega_n8n_crm_connector.whatsapp_debounce_enabled",
            "false",
        )
        return str(value).strip().lower() in {"1", "true", "yes", "y", "si", "sí"}

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
            "\n\n\n[META WHATSAPP VERIFY] mode=%s token_ok=%s challenge_present=%s\n\n\n",
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

        _logger.info("\n\n raw_body -->> %s \n\n", raw_body)

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
                "[META WHATSAPP WEBHOOK] Evento ignorado sin mensajes entrantes hash=%s",
                payload_hash,
            )
            return self._json_response({
                "success": True,
                "ignored": True,
                "reason": "no_inbound_messages",
                "hash": payload_hash,
            })

        if self._is_debounce_enabled() and self._messages_can_be_debounced(messages):
            return self._enqueue_debounced_messages(payload, payload_hash, messages)

        return self._forward_raw_payload_to_n8n(raw_body, payload_hash, messages)

    def _messages_can_be_debounced(self, messages):
        debounceable_types = {"text", "button", "interactive"}
        for message in messages:
            if message.get("message_type") not in debounceable_types:
                _logger.info(
                    "[META WHATSAPP WEBHOOK] Debounce omitido por tipo no-texto wamid=%s type=%s",
                    message.get("external_message_id"),
                    message.get("message_type"),
                )
                return False
        return True

    def _forward_raw_payload_to_n8n(self, raw_body, payload_hash, messages):
        n8n_url = self._get_n8n_webhook_url()
        if not n8n_url:
            _logger.warning(
                "[META WHATSAPP WEBHOOK] URL n8n no configurada hash=%s",
                payload_hash,
            )
            return self._json_response({
                "success": True,
                "forwarded_to_n8n": False,
                "reason": "missing_n8n_url",
                "processed_messages": len(messages),
                "hash": payload_hash,
            })

        try:
            response = requests.post(
                n8n_url,
                data=raw_body.encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "X-Odoo-Webhook-Source": "meta-whatsapp",
                    "X-Odoo-Payload-Hash": payload_hash,
                },
                timeout=10,
            )

            _logger.info(
                "[META WHATSAPP WEBHOOK] Forwarded to n8n status=%s hash=%s messages=%s",
                response.status_code,
                payload_hash,
                len(messages),
            )

        except Exception:
            _logger.exception(
                "[META WHATSAPP WEBHOOK] Error forwarding to n8n hash=%s messages=%s",
                payload_hash,
                len(messages),
            )

        return self._json_response({
            "success": True,
            "forwarded_to_n8n": True,
            "processed_messages": len(messages),
            "hash": payload_hash,
        })

    def _enqueue_debounced_messages(self, payload, payload_hash, messages):
        queue_model = request.env["mega.whatsapp.debounce.queue"].sudo()
        queued = 0
        duplicates = 0
        skipped = 0
        queue_ids = set()

        for message in messages:
            queue, created, reason = queue_model.enqueue_meta_message(
                phone=message.get("phone"),
                phone_number_id=message.get("phone_number_id"),
                wamid=message.get("external_message_id"),
                text=message.get("text"),
                payload=payload,
                raw_message=message.get("raw_message"),
                contact_name=message.get("contact_name"),
                payload_hash=payload_hash,
            )
            if queue:
                queue_ids.add(queue.id)
            if created:
                queued += 1
            elif reason == "duplicate_wamid":
                duplicates += 1
            else:
                skipped += 1

        _logger.info(
            "[META WHATSAPP WEBHOOK] Debounced enqueue hash=%s messages=%s queued=%s duplicates=%s skipped=%s queues=%s",
            payload_hash,
            len(messages),
            queued,
            duplicates,
            skipped,
            sorted(queue_ids),
        )

        return self._json_response({
            "success": True,
            "debounced": True,
            "forwarded_to_n8n": False,
            "processed_messages": len(messages),
            "queued_messages": queued,
            "duplicate_messages": duplicates,
            "skipped_messages": skipped,
            "queue_ids": sorted(queue_ids),
            "hash": payload_hash,
        })


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
                metadata = value.get("metadata") or {}
                phone_number_id = metadata.get("phone_number_id") or ""

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
                            "phone_number_id": phone_number_id,
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
