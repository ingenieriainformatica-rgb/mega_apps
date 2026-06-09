# -*- coding: utf-8 -*-

import importlib.util
import sys
import types
import unittest
from pathlib import Path


CONTROLLER_PATH = (
    Path(__file__).resolve().parents[1]
    / "controllers"
    / "webhook_meta_whatsapp.py"
)


def _install_odoo_stub():
    if "odoo" in sys.modules:
        return

    odoo = types.ModuleType("odoo")
    http = types.ModuleType("odoo.http")

    class Response:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class Controller:
        pass

    def route(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    http.Controller = Controller
    http.route = route
    http.request = types.SimpleNamespace()
    http.Response = Response
    odoo.http = http

    sys.modules["odoo"] = odoo
    sys.modules["odoo.http"] = http


def _load_controller_module():
    _install_odoo_stub()
    module_name = "meta_whatsapp_webhook_controller_test"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, CONTROLLER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


controller_module = _load_controller_module()


class TestMetaWhatsAppMessageMetadata(unittest.TestCase):
    def setUp(self):
        self.controller = controller_module.MetaWhatsAppWebhookController()

    def test_text_metadata(self):
        metadata = self.controller._extract_message_metadata(
            {"type": "text", "text": {"body": "hola"}}
        )

        self.assertEqual(metadata["message_type"], "text")
        self.assertEqual(metadata["text"], "hola")
        self.assertEqual(metadata["media_id"], "")

    def test_image_with_caption_metadata(self):
        metadata = self.controller._extract_message_metadata(
            {
                "type": "image",
                "image": {
                    "id": "media-image-1",
                    "mime_type": "image/jpeg",
                    "caption": "foto bateria",
                },
            }
        )

        self.assertEqual(metadata["message_type"], "image")
        self.assertEqual(metadata["text"], "foto bateria")
        self.assertEqual(metadata["caption"], "foto bateria")
        self.assertEqual(metadata["media_id"], "media-image-1")
        self.assertEqual(metadata["mime_type"], "image/jpeg")

    def test_image_without_caption_metadata(self):
        metadata = self.controller._extract_message_metadata(
            {
                "type": "image",
                "image": {
                    "id": "media-image-2",
                    "mime_type": "image/png",
                },
            }
        )

        self.assertEqual(metadata["message_type"], "image")
        self.assertEqual(metadata["text"], "")
        self.assertEqual(metadata["caption"], "")
        self.assertEqual(metadata["media_id"], "media-image-2")
        self.assertEqual(metadata["mime_type"], "image/png")

    def test_audio_metadata(self):
        metadata = self.controller._extract_message_metadata(
            {
                "type": "audio",
                "audio": {
                    "id": "media-audio-1",
                    "mime_type": "audio/ogg",
                    "voice": True,
                },
            }
        )

        self.assertEqual(metadata["message_type"], "audio")
        self.assertEqual(metadata["text"], "")
        self.assertEqual(metadata["media_id"], "media-audio-1")
        self.assertEqual(metadata["mime_type"], "audio/ogg")
        self.assertTrue(metadata["voice"])

    def test_location_metadata(self):
        metadata = self.controller._extract_message_metadata(
            {
                "type": "location",
                "location": {
                    "latitude": 6.2442,
                    "longitude": -75.5812,
                    "name": "Centro",
                    "address": "Medellin, Antioquia",
                },
            }
        )

        self.assertEqual(metadata["message_type"], "location")
        self.assertEqual(metadata["text"], "")
        self.assertEqual(metadata["latitude"], 6.2442)
        self.assertEqual(metadata["longitude"], -75.5812)
        self.assertEqual(metadata["location_name"], "Centro")
        self.assertEqual(metadata["location_address"], "Medellin, Antioquia")

    def test_unknown_metadata(self):
        metadata = self.controller._extract_message_metadata({"type": "sticker"})

        self.assertEqual(metadata["message_type"], "sticker")
        self.assertEqual(metadata["text"], "")
        self.assertEqual(metadata["media_id"], "")

    def test_payload_includes_normalized_messages(self):
        payload = {"entry": [{"changes": [{"value": {"messages": []}}]}]}
        messages = [
            {
                "phone": "573001112233",
                "phone_number_id": "12345",
                "contact_name": "Cliente",
                "external_message_id": "wamid.1",
                "message_type": "audio",
                "text": "",
                "media_id": "media-audio-1",
                "mime_type": "audio/ogg",
                "caption": "",
                "latitude": None,
                "longitude": None,
                "location_name": "",
                "location_address": "",
                "voice": True,
            }
        ]

        enriched = self.controller._with_normalized_messages(payload, messages)

        self.assertEqual(enriched["normalized_messages"][0]["message_type"], "audio")
        self.assertEqual(enriched["normalized_messages"][0]["media_id"], "media-audio-1")
        self.assertTrue(enriched["normalized_messages"][0]["voice"])


if __name__ == "__main__":
    unittest.main()
