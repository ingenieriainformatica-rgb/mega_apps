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

        _logger.info(
            "[WHATSAPP META] inbound webhook received keys=%s",
            list(payload.keys()) if isinstance(payload, dict) else type(payload),
        )

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

        enriched_payload = self._with_normalized_messages(payload, messages)
        enriched_raw_body = json.dumps(enriched_payload, ensure_ascii=False)

        if self._is_debounce_enabled() and self._messages_can_be_debounced(messages):
            return self._enqueue_debounced_messages(enriched_payload, payload_hash, messages)

        return self._forward_raw_payload_to_n8n(enriched_raw_body, payload_hash, messages)

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
                    metadata = self._extract_message_metadata(message)
                    message_type = metadata.get("message_type")
                    text = metadata.get("text")

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

                    media_id = metadata.get("media_id") or ""
                    _logger.info(
                        "[WHATSAPP META] normalized type=%s phone=%s phone_number_id=%s media_id=%s message_id=%s",
                        message_type,
                        phone,
                        phone_number_id,
                        media_id,
                        external_message_id,
                    )

                    result.append(
                        {
                            "phone": phone,
                            "phone_number_id": phone_number_id,
                            "contact_name": contact_name,
                            "external_message_id": external_message_id,
                            "message_type": message_type,
                            "text": text,
                            **metadata,
                            "raw_message": message,
                        }
                    )

        return result

    def _with_normalized_messages(self, payload, messages):
        enriched_payload = json.loads(json.dumps(payload))
        normalized_messages = [
            self._normalized_message_for_payload(message)
            for message in messages
        ]
        enriched_payload["normalized_messages"] = normalized_messages
        return enriched_payload

    def _normalized_message_for_payload(self, message):
        return {
            "phone": message.get("phone") or "",
            "phone_number_id": message.get("phone_number_id") or "",
            "contact_name": message.get("contact_name") or "",
            "external_message_id": message.get("external_message_id") or "",
            "wamid": message.get("external_message_id") or "",
            "message_type": message.get("message_type") or "",
            "text": message.get("text") or "",
            "media_id": message.get("media_id") or "",
            "mime_type": message.get("mime_type") or "",
            "caption": message.get("caption") or "",
            "latitude": message.get("latitude"),
            "longitude": message.get("longitude"),
            "location_name": message.get("location_name") or "",
            "location_address": message.get("location_address") or "",
            "voice": bool(message.get("voice")),
            "unsupported_message": bool(message.get("unsupported_message")),
            "control_reply": message.get("control_reply") or "",
            "should_use_ai": bool(message.get("should_use_ai", True)),
            "should_send": bool(message.get("should_send", False)),
        }

    def _control_reply_for_message_type(self, message_type):
        if message_type == "image":
            return (
                "Recibimos tu imagen. Para ayudarte con la batería, por favor "
                "escríbenos el vehículo, la ubicación y qué necesitas revisar."
            )

        if message_type == "audio":
            return (
                "Recibimos tu audio, pero para atenderte más rápido por este canal "
                "por favor envíanos la información por texto: vehículo, ubicación y solicitud."
            )

        return (
            "Recibimos tu mensaje, pero necesitamos que nos escribas por texto el "
            "vehículo, la ubicación y qué necesitas para poder ayudarte."
        )

    def _mark_unsupported_without_text(self, metadata):
        metadata.update(
            {
                "unsupported_message": True,
                "control_reply": self._control_reply_for_message_type(
                    metadata.get("message_type")
                ),
                "should_use_ai": False,
                "should_send": True,
            }
        )
        return metadata

    def _extract_message_metadata(self, message):
        message_type = message.get("type") or "unknown"
        metadata = {
            "message_type": message_type,
            "text": "",
            "media_id": "",
            "mime_type": "",
            "caption": "",
            "latitude": None,
            "longitude": None,
            "location_name": "",
            "location_address": "",
            "voice": False,
            "unsupported_message": False,
            "control_reply": "",
            "should_use_ai": True,
            "should_send": False,
        }

        if message_type == "text":
            metadata["text"] = (message.get("text") or {}).get("body") or ""
            _logger.info(f"\n\n text -> {metadata['text']} \n\n")
            return metadata if metadata["text"] else self._mark_unsupported_without_text(metadata)

        if message_type == "button":
            metadata["text"] = (message.get("button") or {}).get("text") or ""
            _logger.info(f"\n\n button -> {metadata['text']} \n\n")
            return metadata if metadata["text"] else self._mark_unsupported_without_text(metadata)

        if message_type == "interactive":
            interactive = message.get("interactive") or {}

            button_reply = interactive.get("button_reply") or {}
            if button_reply:
                metadata["text"] = button_reply.get("title") or button_reply.get("id") or ""
                return metadata

            list_reply = interactive.get("list_reply") or {}
            if list_reply:
                metadata["text"] = list_reply.get("title") or list_reply.get("id") or ""
                return metadata

            return self._mark_unsupported_without_text(metadata)

        if message_type == "location":
            location = message.get("location") or {}
            metadata.update(
                {
                    "latitude": location.get("latitude"),
                    "longitude": location.get("longitude"),
                    "location_name": location.get("name") or "",
                    "location_address": location.get("address") or "",
                }
            )
            return self._mark_unsupported_without_text(metadata)

        if message_type == "image":
            image = message.get("image") or {}
            caption = image.get("caption") or ""
            metadata.update(
                {
                    "text": caption,
                    "media_id": image.get("id") or "",
                    "mime_type": image.get("mime_type") or "",
                    "caption": caption,
                }
            )
            return metadata

        if message_type == "audio":
            audio = message.get("audio") or {}
            _logger.info(f"\n\n audio -> {metadata['text']} \n\n")
            metadata.update(
                {
                    "media_id": audio.get("id") or "",
                    "mime_type": audio.get("mime_type") or "",
                    "voice": bool(audio.get("voice")),
                }
            )
            return metadata

        if message_type == "document":
            document = message.get("document") or {}
            metadata.update(
                {
                    "media_id": document.get("id") or "",
                    "mime_type": document.get("mime_type") or "",
                }
            )
            return self._mark_unsupported_without_text(metadata)

        return self._mark_unsupported_without_text(metadata)

    def _extract_message_text(self, message):
        """
        Obtiene texto visible según el tipo de mensaje.
        """
        metadata = self._extract_message_metadata(message)
        if metadata["text"]:
            return metadata["text"]

        message_type = metadata["message_type"]
        if message_type == "document":
            document = message.get("document") or {}
            filename = document.get("filename") or "documento"
            return "[Documento recibido: %s]" % filename

        return ""
