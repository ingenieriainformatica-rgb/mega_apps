# -*- coding: utf-8 -*-

import copy
import hashlib
import json
import logging
from datetime import timedelta

import requests

from odoo import _, api, fields, models  # type: ignore

_logger = logging.getLogger(__name__)


DEBOUNCE_SECONDS = 9
DEBOUNCE_CHANNEL = "root.whatsapp_debounce"


class MegaWhatsappDebounceQueue(models.Model):
    _name = "mega.whatsapp.debounce.queue"
    _description = "WhatsApp inbound debounce queue"
    _order = "last_message_at desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    phone = fields.Char(required=True, index=True)
    phone_number_id = fields.Char(index=True)
    active_key = fields.Char(index=True)
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("done", "Done"),
            ("failed", "Failed"),
        ],
        default="pending",
        required=True,
        index=True,
    )
    first_message_at = fields.Datetime(required=True, index=True)
    last_message_at = fields.Datetime(required=True, index=True)
    job_uuid = fields.Char(index=True)
    processed_at = fields.Datetime()
    n8n_status_code = fields.Integer()
    error_message = fields.Text()
    message_count = fields.Integer(compute="_compute_message_count", store=True)
    message_ids = fields.One2many(
        "mega.whatsapp.debounce.message",
        "queue_id",
        string="Messages",
    )

    _sql_constraints = [
        (
            "unique_active_key",
            "unique(active_key)",
            "There is already an active WhatsApp debounce queue for this customer and account.",
        ),
    ]

    @api.depends("phone", "phone_number_id", "state")
    def _compute_name(self):
        for queue in self:
            account = queue.phone_number_id or "no-account"
            queue.name = "%s / %s / %s" % (queue.phone or "", account, queue.state or "")

    @api.depends("message_ids")
    def _compute_message_count(self):
        for queue in self:
            queue.message_count = len(queue.message_ids)

    @api.model
    def _make_active_key(self, phone, phone_number_id):
        return "%s|%s" % ((phone or "").strip(), (phone_number_id or "").strip())

    @api.model
    def enqueue_meta_message(
        self,
        *,
        phone,
        phone_number_id,
        wamid,
        text,
        payload,
        raw_message,
        contact_name=None,
        payload_hash=None,
    ):
        phone = (phone or "").strip()
        phone_number_id = (phone_number_id or "").strip()
        wamid = (wamid or "").strip()
        now = fields.Datetime.now()

        if not phone or not wamid:
            return self.browse(), False, "missing_phone_or_wamid"

        line_model = self.env["mega.whatsapp.debounce.message"].sudo()
        existing_line = line_model.search([("wamid", "=", wamid)], limit=1)
        if existing_line:
            _logger.info(
                "[WHATSAPP DEBOUNCE] duplicate wamid ignored wamid=%s queue_id=%s",
                wamid,
                existing_line.queue_id.id,
            )
            return existing_line.queue_id, False, "duplicate_wamid"

        active_key = self._make_active_key(phone, phone_number_id)
        queue = self._get_or_create_active_queue(phone, phone_number_id, active_key, now)

        try:
            with self.env.cr.savepoint():
                line_model.create(
                    {
                        "queue_id": queue.id,
                        "wamid": wamid,
                        "phone": phone,
                        "phone_number_id": phone_number_id,
                        "contact_name": contact_name,
                        "text": text or "",
                        "payload": payload,
                        "raw_message": raw_message,
                        "payload_hash": payload_hash,
                        "received_at": now,
                    }
                )
        except Exception:
            existing_line = line_model.search([("wamid", "=", wamid)], limit=1)
            if existing_line:
                _logger.info(
                    "[WHATSAPP DEBOUNCE] duplicate wamid ignored after race wamid=%s queue_id=%s",
                    wamid,
                    existing_line.queue_id.id,
                )
                return existing_line.queue_id, False, "duplicate_wamid"
            raise

        if queue.state in ("done", "failed"):
            queue.write(
                {
                    "state": "pending",
                    "active_key": active_key,
                    "error_message": False,
                    "n8n_status_code": False,
                    "processed_at": False,
                }
            )

        queue.write({"last_message_at": now})
        queue._schedule_debounce_job(now + timedelta(seconds=DEBOUNCE_SECONDS))

        _logger.info(
            "[WHATSAPP DEBOUNCE] queued message queue_id=%s wamid=%s phone=%s phone_number_id=%s eta=%s count=%s",
            queue.id,
            wamid,
            phone,
            phone_number_id,
            now + timedelta(seconds=DEBOUNCE_SECONDS),
            queue.message_count,
        )
        return queue, True, "queued"

    @api.model
    def _get_or_create_active_queue(self, phone, phone_number_id, active_key, now):
        queue = self.sudo().search(
            [
                ("active_key", "=", active_key),
                ("state", "in", ("pending", "processing")),
            ],
            limit=1,
        )
        if queue:
            return queue

        values = {
            "phone": phone,
            "phone_number_id": phone_number_id,
            "active_key": active_key,
            "state": "pending",
            "first_message_at": now,
            "last_message_at": now,
        }
        try:
            with self.env.cr.savepoint():
                return self.sudo().create(values)
        except Exception:
            queue = self.sudo().search(
                [
                    ("active_key", "=", active_key),
                    ("state", "in", ("pending", "processing")),
                ],
                limit=1,
            )
            if queue:
                return queue
            raise

    def _schedule_debounce_job(self, eta):
        self.ensure_one()
        job = self.with_delay(
            eta=eta,
            channel=DEBOUNCE_CHANNEL,
            description=_("WhatsApp debounce queue %s") % self.id,
        )._process_debounce_job()
        job_uuid = getattr(job, "uuid", False)
        self.write({"job_uuid": job_uuid})
        _logger.info(
            "[WHATSAPP DEBOUNCE] scheduled job queue_id=%s job_uuid=%s eta=%s",
            self.id,
            job_uuid,
            eta,
        )
        return job

    def _process_debounce_job(self):
        for queue in self.sudo():
            queue.invalidate_recordset()
            if queue.state not in ("pending", "processing"):
                _logger.info(
                    "[WHATSAPP DEBOUNCE] job skipped queue_id=%s state=%s",
                    queue.id,
                    queue.state,
                )
                continue

            now = fields.Datetime.now()
            due_at = queue.last_message_at + timedelta(seconds=DEBOUNCE_SECONDS)
            if now < due_at:
                queue._schedule_debounce_job(due_at)
                _logger.info(
                    "[WHATSAPP DEBOUNCE] queue_id=%s not due now=%s due_at=%s rescheduled",
                    queue.id,
                    now,
                    due_at,
                )
                continue

            queue.write({"state": "processing"})
            try:
                payload = queue._build_debounced_payload()
                status_code = queue._send_debounced_payload(payload)
                queue.write(
                    {
                        "state": "done",
                        "active_key": False,
                        "processed_at": fields.Datetime.now(),
                        "n8n_status_code": status_code,
                        "error_message": False,
                    }
                )
                _logger.info(
                    "[WHATSAPP DEBOUNCE] sent queue_id=%s status=%s messages=%s wamids=%s",
                    queue.id,
                    status_code,
                    queue.message_count,
                    queue.message_ids.mapped("wamid"),
                )
            except Exception as exc:
                queue.write(
                    {
                        "state": "failed",
                        "active_key": False,
                        "processed_at": fields.Datetime.now(),
                        "error_message": str(exc),
                    }
                )
                _logger.exception(
                    "[WHATSAPP DEBOUNCE] failed queue_id=%s messages=%s error=%s",
                    queue.id,
                    queue.message_count,
                    exc,
                )

        return True

    def _send_debounced_payload(self, payload):
        self.ensure_one()
        config = self.env["ir.config_parameter"].sudo()
        n8n_url = config.get_param("mega_n8n_crm_connector.n8n_inbound_webhook_url")
        if not n8n_url:
            raise ValueError("missing_n8n_url")

        raw_body = json.dumps(payload, ensure_ascii=False)
        payload_hash = hashlib.sha256(raw_body.encode("utf-8")).hexdigest()[:16]
        response = requests.post(
            n8n_url,
            data=raw_body.encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Odoo-Webhook-Source": "meta-whatsapp",
                "X-Odoo-Payload-Hash": payload_hash,
                "X-Odoo-WhatsApp-Debounced": "true",
                "X-Odoo-WhatsApp-Debounce-Queue-Id": str(self.id),
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.status_code

    def _build_debounced_payload(self):
        self.ensure_one()
        lines = self.message_ids.sorted(lambda line: (line.received_at, line.id))
        if not lines:
            raise ValueError("empty_debounce_queue")

        base_payload = copy.deepcopy(lines[0].payload or {})
        original_message_ids = [line.wamid for line in lines if line.wamid]
        consolidated_text = "\n".join((line.text or "").strip() for line in lines).strip()

        first_entry, first_change, value = self._get_first_value(base_payload)
        first_message = copy.deepcopy(lines[0].raw_message or {})
        first_message["type"] = "text"
        first_message["id"] = original_message_ids[0] if original_message_ids else first_message.get("id")
        first_message["from"] = self.phone
        first_message["text"] = {"body": consolidated_text}

        value["messages"] = [first_message]
        value.setdefault("metadata", {})
        value["metadata"]["phone_number_id"] = self.phone_number_id
        if first_change is not None:
            first_change["value"] = value
        if first_entry is not None:
            first_entry["changes"] = [first_change]
            base_payload["entry"] = [first_entry]

        metadata = {
            "debounced": True,
            "debounce_queue_id": self.id,
            "original_message_ids": original_message_ids,
            "original_message_count": len(original_message_ids),
        }
        base_payload.update(metadata)
        value.update(metadata)
        return base_payload

    def _get_first_value(self, payload):
        entries = payload.setdefault("entry", [{}])
        if not entries:
            entries.append({})
        first_entry = entries[0]
        changes = first_entry.setdefault("changes", [{}])
        if not changes:
            changes.append({})
        first_change = changes[0]
        value = first_change.setdefault("value", {})
        return first_entry, first_change, value


class MegaWhatsappDebounceMessage(models.Model):
    _name = "mega.whatsapp.debounce.message"
    _description = "WhatsApp inbound debounce message"
    _order = "received_at asc, id asc"

    queue_id = fields.Many2one(
        "mega.whatsapp.debounce.queue",
        required=True,
        ondelete="cascade",
        index=True,
    )
    wamid = fields.Char(required=True, index=True)
    phone = fields.Char(required=True, index=True)
    phone_number_id = fields.Char(index=True)
    contact_name = fields.Char()
    text = fields.Text()
    payload = fields.Json()
    raw_message = fields.Json()
    payload_hash = fields.Char(index=True)
    received_at = fields.Datetime(default=fields.Datetime.now, required=True, index=True)

    _sql_constraints = [
        (
            "unique_wamid",
            "unique(wamid)",
            "This WhatsApp message id is already queued.",
        ),
    ]
