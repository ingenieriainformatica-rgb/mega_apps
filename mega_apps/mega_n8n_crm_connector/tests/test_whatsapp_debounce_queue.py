# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import fields  # type: ignore
from odoo.tests import TransactionCase, tagged  # type: ignore


@tagged("post_install", "-at_install")
class TestWhatsAppDebounceQueue(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Queue = self.env["mega.whatsapp.debounce.queue"].sudo()
        self.sent_payloads = []
        self._original_send = type(self.Queue)._send_debounced_payload
        self._original_schedule = type(self.Queue)._schedule_debounce_job

        def fake_send(recordset, payload):
            self.sent_payloads.append((recordset.id, payload))
            return 200

        def fake_schedule(recordset, eta):
            recordset.write({"job_uuid": "fake-job-%s" % recordset.id})
            return None

        type(self.Queue)._send_debounced_payload = fake_send
        type(self.Queue)._schedule_debounce_job = fake_schedule

    def tearDown(self):
        type(self.Queue)._send_debounced_payload = self._original_send
        type(self.Queue)._schedule_debounce_job = self._original_schedule
        super().tearDown()

    def _payload(self, phone, phone_number_id, wamid, text):
        return {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WABA_TEST",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": phone_number_id},
                                "contacts": [
                                    {"wa_id": phone, "profile": {"name": "Cliente Test"}}
                                ],
                                "messages": [
                                    {
                                        "from": phone,
                                        "id": wamid,
                                        "timestamp": "1780000000",
                                        "type": "text",
                                        "text": {"body": text},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

    def _enqueue(self, phone, phone_number_id, wamid, text):
        payload = self._payload(phone, phone_number_id, wamid, text)
        raw_message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
        return self.Queue.enqueue_meta_message(
            phone=phone,
            phone_number_id=phone_number_id,
            wamid=wamid,
            text=text,
            payload=payload,
            raw_message=raw_message,
            contact_name="Cliente Test",
            payload_hash="hash-" + wamid,
        )

    def _process_due(self, queue):
        queue.write({"last_message_at": fields.Datetime.now() - timedelta(seconds=10)})
        queue._process_debounce_job()
        queue.invalidate_recordset()
        return queue

    def _last_body(self):
        payload = self.sent_payloads[-1][1]
        return payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]

    def test_single_message_sends_one_payload(self):
        queue, created, reason = self._enqueue(
            "57UNIT001", "PNID_A", "wamid.UNIT.001", "hola"
        )

        self.assertTrue(created)
        self.assertEqual(reason, "queued")
        self._process_due(queue)

        self.assertEqual(queue.state, "done")
        self.assertEqual(len(self.sent_payloads), 1)
        self.assertEqual(self._last_body(), "hola")

    def test_fast_messages_are_consolidated(self):
        queue, _, _ = self._enqueue("57UNIT002", "PNID_A", "wamid.UNIT.002a", "hola")
        self._enqueue("57UNIT002", "PNID_A", "wamid.UNIT.002b", "como estas")
        self._enqueue("57UNIT002", "PNID_A", "wamid.UNIT.002c", "necesito bateria")

        self._process_due(queue)

        self.assertEqual(queue.state, "done")
        self.assertEqual(len(queue.message_ids), 3)
        self.assertEqual(self._last_body(), "hola\ncomo estas\nnecesito bateria")
        self.assertEqual(self.sent_payloads[-1][1]["original_message_count"], 3)

    def test_separated_messages_create_separate_queues(self):
        first_queue, _, _ = self._enqueue(
            "57UNIT003", "PNID_A", "wamid.UNIT.003a", "hola"
        )
        self._process_due(first_queue)
        second_queue, _, _ = self._enqueue(
            "57UNIT003", "PNID_A", "wamid.UNIT.003b", "necesito bateria"
        )
        self._process_due(second_queue)

        self.assertNotEqual(first_queue.id, second_queue.id)
        self.assertEqual(len(self.sent_payloads), 2)

    def test_duplicate_wamid_is_not_queued_twice(self):
        queue, created, reason = self._enqueue(
            "57UNIT004", "PNID_A", "wamid.UNIT.004", "hola"
        )
        duplicate_queue, duplicate_created, duplicate_reason = self._enqueue(
            "57UNIT004", "PNID_A", "wamid.UNIT.004", "hola duplicado"
        )

        self.assertEqual(queue, duplicate_queue)
        self.assertTrue(created)
        self.assertEqual(reason, "queued")
        self.assertFalse(duplicate_created)
        self.assertEqual(duplicate_reason, "duplicate_wamid")
        self.assertEqual(len(queue.message_ids), 1)

    def test_different_clients_are_not_mixed(self):
        queue_a, _, _ = self._enqueue("57UNIT005A", "PNID_A", "wamid.UNIT.005a1", "hola A")
        self._enqueue("57UNIT005A", "PNID_A", "wamid.UNIT.005a2", "mensaje A")
        queue_b, _, _ = self._enqueue("57UNIT005B", "PNID_A", "wamid.UNIT.005b1", "hola B")
        self._enqueue("57UNIT005B", "PNID_A", "wamid.UNIT.005b2", "mensaje B")

        self._process_due(queue_a)
        self._process_due(queue_b)

        self.assertNotEqual(queue_a.id, queue_b.id)
        self.assertEqual(len(queue_a.message_ids), 2)
        self.assertEqual(len(queue_b.message_ids), 2)
        self.assertEqual(self.sent_payloads[-2][1]["original_message_count"], 2)
        self.assertEqual(self.sent_payloads[-1][1]["original_message_count"], 2)

    def test_not_due_queue_is_rescheduled_without_sending(self):
        queue, _, _ = self._enqueue(
            "57UNIT006", "PNID_A", "wamid.UNIT.006", "hola"
        )

        queue._process_debounce_job()
        queue.invalidate_recordset()

        self.assertEqual(queue.state, "pending")
        self.assertEqual(len(self.sent_payloads), 0)
        self.assertTrue(queue.job_uuid)

    def test_n8n_failure_marks_queue_failed(self):
        def failing_send(recordset, payload):
            raise RuntimeError("n8n test failure")

        type(self.Queue)._send_debounced_payload = failing_send
        queue, _, _ = self._enqueue("57UNIT007", "PNID_A", "wamid.UNIT.007", "hola")

        self._process_due(queue)

        self.assertEqual(queue.state, "failed")
        self.assertIn("n8n test failure", queue.error_message)
