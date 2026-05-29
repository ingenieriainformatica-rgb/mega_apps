# -*- coding: utf-8 -*-

import importlib.util
import sys
import types
import unittest
from pathlib import Path


HELPERS_DIR = Path(__file__).resolve().parents[1] / "helpers"
PACKAGE_ROOT = "mega_n8n_crm_connector_test"
HELPERS_PACKAGE = f"{PACKAGE_ROOT}.helpers"


def _install_odoo_stub():
    if "odoo" in sys.modules:
        return

    odoo = types.ModuleType("odoo")
    odoo.fields = types.SimpleNamespace(
        Datetime=types.SimpleNamespace(
            subtract=lambda *args, **kwargs: None,
            now=lambda: None,
        )
    )
    sys.modules["odoo"] = odoo


def _load_helper_module(module_name):
    sys.modules.setdefault(PACKAGE_ROOT, types.ModuleType(PACKAGE_ROOT))
    sys.modules.setdefault(HELPERS_PACKAGE, types.ModuleType(HELPERS_PACKAGE))

    full_name = f"{HELPERS_PACKAGE}.{module_name}"
    if full_name in sys.modules:
        return sys.modules[full_name]

    spec = importlib.util.spec_from_file_location(
        full_name,
        HELPERS_DIR / f"{module_name}.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


def _load_progressive_helper():
    _install_odoo_stub()
    for module_name in (
        "constants",
        "whatsapp_messages",
        "whatsapp_vehicle_helper",
        "whatsapp_session_helper",
        "whatsapp_ai_prompt",
    ):
        _load_helper_module(module_name)
    return sys.modules[f"{HELPERS_PACKAGE}.whatsapp_session_helper"]


helper = _load_progressive_helper()
prompt = sys.modules[f"{HELPERS_PACKAGE}.whatsapp_ai_prompt"]


class FakeSession(types.SimpleNamespace):
    _fields = {
        "customer_name": True,
        "vehicle_brand": True,
        "vehicle_model": True,
        "vehicle_year": True,
        "vehicle_type": True,
        "vehicle_info": True,
        "city": True,
        "neighborhood": True,
        "location": True,
        "plate": True,
        "battery_request": True,
        "relevant_data": True,
        "conversation_summary": True,
        "welcome_sent": True,
    }


def make_session(**overrides):
    data = {
        "step": "ask_name",
        "customer_name": "",
        "vehicle_brand": "",
        "vehicle_model": "",
        "vehicle_year": "",
        "vehicle_type": "",
        "vehicle_info": "",
        "city": "",
        "neighborhood": "",
        "location": "",
        "plate": "",
        "battery_request": False,
        "relevant_data": "",
        "conversation_summary": "",
        "welcome_sent": False,
        "customer_leaves_old_battery": True,
        "last_message": "",
    }
    data.update(overrides)
    return FakeSession(**data)


def apply_ai(session, ai_result):
    next_step, should_send, reply, vals = helper.build_ai_session_update(
        session,
        ai_result,
    )
    for key, value in vals.items():
        setattr(session, key, value)
    return next_step, should_send, reply, vals


class TestProgressiveDataCapture(unittest.TestCase):
    def test_first_contact_prompt_includes_full_welcome_rules(self):
        session = make_session(
            welcome_sent=False,
            last_message="Hola vengo de la web",
        )

        instruction = prompt.get_ai_instruction(session, session.last_message)

        self.assertIn("current_welcome_sent:", instruction)
        self.assertIn("False", instruction)
        self.assertIn("Hola 👋 Bienvenido a Mega Baterías.", instruction)
        self.assertIn("Atendemos Medellín y Área Metropolitana", instruction)
        self.assertIn("Horario: lunes a sábado de 7:00 a.m. a 6:00 p.m.", instruction)
        self.assertIn("carros, camionetas y camiones", instruction)

    def test_prompt_prevents_repeating_welcome_after_it_was_sent(self):
        session = make_session(
            welcome_sent=True,
            customer_name="Jorge",
            vehicle_brand="Mazda",
            vehicle_model="3",
            last_message="2024",
        )

        instruction = prompt.get_ai_instruction(session, session.last_message)

        self.assertIn("current_welcome_sent:", instruction)
        self.assertIn("True", instruction)
        self.assertIn("NO digas \"Bienvenido a Mega Baterías\"", instruction)
        self.assertIn("NO repitas cobertura", instruction)
        self.assertIn("NO repitas horario", instruction)

    def test_name_vehicle_year_and_city_can_advance(self):
        session = make_session(
            last_message="Hola, soy Carlos, tengo un Mazda 3 2018 y estoy en Medellin."
        )

        next_step, should_send, reply, vals = apply_ai(
            session,
            {
                "intent": "progressive_data_capture",
                "customer_name": "Carlos",
                "vehicle_brand": "Mazda",
                "vehicle_model": "3",
                "vehicle_year": "2018",
                "city": "Medellin",
                "location": "Medellin",
                "battery_request": True,
                "can_advance": True,
                "next_step": "confirm_data",
                "assistant_message": "Confirmemos tus datos para continuar.",
            },
        )

        self.assertEqual(next_step, "confirm_data")
        self.assertTrue(should_send)
        self.assertEqual(vals["customer_name"], "Carlos")
        self.assertEqual(vals["vehicle_brand"], "Mazda")
        self.assertEqual(vals["vehicle_model"], "3")
        self.assertEqual(vals["vehicle_year"], "2018")
        self.assertEqual(vals["city"], "Medellin")
        self.assertEqual(vals["location"], "Medellin")
        self.assertNotIn("regalas por favor tu nombre", reply.lower())

    def test_vehicle_year_without_name_keeps_vehicle_and_asks_only_name(self):
        session = make_session(last_message="Tengo un Mazda 3 2018.")

        next_step, should_send, reply, vals = apply_ai(
            session,
            {
                "intent": "progressive_data_capture",
                "vehicle_brand": "Mazda",
                "vehicle_model": "3",
                "vehicle_year": "2018",
                "battery_request": True,
                "can_advance": False,
                "next_required_field": "customer_name",
                "assistant_message": (
                    "Perfecto. Ya tengo los datos de tu Mazda 3 2018. "
                    "Me confirmas por favor tu nombre para continuar?"
                ),
            },
        )

        self.assertEqual(next_step, "ask_name")
        self.assertTrue(should_send)
        self.assertEqual(vals["vehicle_info"], "Mazda 3 2018")
        self.assertEqual(vals["vehicle_brand"], "Mazda")
        self.assertEqual(vals["vehicle_model"], "3")
        self.assertEqual(vals["vehicle_year"], "2018")
        self.assertIn("nombre", reply.lower())
        self.assertNotIn("vehiculo", reply.lower())

    def test_greeting_only_does_not_invent_data(self):
        session = make_session(last_message="Hola, buenos dias.")

        next_step, should_send, reply, vals = apply_ai(
            session,
            {
                "intent": "progressive_data_capture",
                "can_advance": False,
                "next_required_field": "customer_name",
                "assistant_message": "Hola, con gusto te ayudo. Me regalas por favor tu nombre?",
            },
        )

        self.assertEqual(next_step, "ask_name")
        self.assertTrue(should_send)
        self.assertNotIn("customer_name", vals)
        self.assertNotIn("vehicle_info", vals)
        self.assertNotIn("location", vals)
        self.assertIn("nombre", reply.lower())

    def test_name_only_then_asks_for_vehicle(self):
        session = make_session(last_message="Soy Andres.")

        next_step, should_send, reply, vals = apply_ai(
            session,
            {
                "intent": "progressive_data_capture",
                "customer_name": "Andres",
                "can_advance": True,
                "next_required_field": "vehicle_brand",
                "assistant_message": (
                    "Gracias Andres. Ahora indicame por favor la marca, "
                    "modelo y ano de tu vehiculo."
                ),
            },
        )

        self.assertEqual(next_step, "ask_vehicle")
        self.assertTrue(should_send)
        self.assertEqual(vals["customer_name"], "Andres")
        self.assertIn("marca", reply.lower())
        self.assertIn("vehiculo", reply.lower())

    def test_doubtful_name_is_not_saved(self):
        session = make_session(last_message="Soy yo.")

        next_step, should_send, reply, vals = apply_ai(
            session,
            {
                "intent": "progressive_data_capture",
                "customer_name": "yo",
                "can_advance": False,
                "next_required_field": "customer_name",
                "assistant_message": "Me confirmas por favor tu nombre para continuar?",
            },
        )

        self.assertEqual(next_step, "ask_name")
        self.assertTrue(should_send)
        self.assertNotIn("customer_name", vals)
        self.assertIn("nombre", reply.lower())

    def test_data_in_separate_messages_is_preserved(self):
        session = make_session(last_message="Tengo un Spark 2016.")

        apply_ai(
            session,
            {
                "intent": "progressive_data_capture",
                "vehicle_brand": "Chevrolet",
                "vehicle_model": "Spark",
                "vehicle_year": "2016",
                "battery_request": True,
                "next_required_field": "customer_name",
                "assistant_message": "Perfecto. Me confirmas por favor tu nombre?",
            },
        )

        self.assertEqual(session.vehicle_info, "Chevrolet Spark 2016")
        self.assertEqual(session.vehicle_model, "Spark")

        session.last_message = "Soy Laura."
        apply_ai(
            session,
            {
                "intent": "progressive_data_capture",
                "customer_name": "Laura",
                "next_required_field": "city",
                "assistant_message": "Gracias Laura. En que ciudad o barrio te encuentras?",
            },
        )

        self.assertEqual(session.customer_name, "Laura")
        self.assertEqual(session.vehicle_info, "Chevrolet Spark 2016")
        self.assertEqual(session.vehicle_model, "Spark")

        session.last_message = "Estoy en Bello."
        next_step, should_send, reply, vals = apply_ai(
            session,
            {
                "intent": "progressive_data_capture",
                "city": "Bello",
                "location": "Bello",
                "can_advance": True,
                "next_step": "confirm_data",
                "assistant_message": "Confirmemos tus datos para continuar.",
            },
        )

        self.assertEqual(next_step, "confirm_data")
        self.assertTrue(should_send)
        self.assertEqual(session.customer_name, "Laura")
        self.assertEqual(session.vehicle_model, "Spark")
        self.assertEqual(session.vehicle_year, "2016")
        self.assertEqual(session.city, "Bello")
        self.assertEqual(session.location, "Bello")

    def test_misspelled_brand_is_normalized_in_backend(self):
        session = make_session(
            welcome_sent=True,
            last_message="Soy Jorge tengo una masda 3",
        )

        next_step, should_send, reply, vals = apply_ai(
            session,
            {
                "intent": "progressive_data_capture",
                "customer_name": "Jorge",
                "vehicle_brand": "masda",
                "vehicle_model": "3",
                "next_required_field": "vehicle_year",
                "assistant_message": (
                    "Perfecto Jorge 👍\n\n"
                    "Ya tengo registrado:\n"
                    "🚗 Marca: Mazda\n"
                    "🚗 Modelo: 3\n\n"
                    "¿Me compartes por favor el año del vehículo?"
                ),
            },
        )

        self.assertEqual(next_step, "ask_vehicle")
        self.assertTrue(should_send)
        self.assertEqual(vals["customer_name"], "Jorge")
        self.assertEqual(vals["vehicle_brand"], "Mazda")
        self.assertEqual(vals["vehicle_model"], "3")
        self.assertIn("Mazda", reply)

    def test_masdaa_brand_is_normalized_in_backend(self):
        session = make_session(
            welcome_sent=True,
            last_message="masdaa 3 2024",
        )

        next_step, should_send, reply, vals = apply_ai(
            session,
            {
                "intent": "progressive_data_capture",
                "vehicle_brand": "masdaa",
                "vehicle_model": "3",
                "vehicle_year": "2024",
                "next_required_field": "customer_name",
                "assistant_message": (
                    "Ya tengo registrado:\n"
                    "🚗 Marca: Mazda\n"
                    "🚗 Modelo: 3\n"
                    "🚗 Año: 2024\n\n"
                    "¿Me confirmas por favor tu nombre?"
                ),
            },
        )

        self.assertEqual(next_step, "ask_name")
        self.assertTrue(should_send)
        self.assertEqual(vals["vehicle_brand"], "Mazda")
        self.assertEqual(vals["vehicle_model"], "3")
        self.assertEqual(vals["vehicle_year"], "2024")

    def test_full_welcome_reply_is_detected_and_marks_session(self):
        session = make_session(welcome_sent=False)
        reply = (
            "Hola 👋 Bienvenido a Mega Baterías.\n\n"
            "📍 Atendemos Medellín y Área Metropolitana.\n"
            "🕒 Horario: lunes a sábado de 7:00 a.m. a 6:00 p.m.\n"
            "🔋 Solo manejamos baterías para carros, camionetas y camiones.\n"
        )

        self.assertTrue(helper.reply_contains_full_welcome(reply))
        updated = helper.mark_welcome_sent_on_session(
            session,
            helper.reply_contains_full_welcome(reply),
        )

        self.assertTrue(updated)
        self.assertTrue(session.welcome_sent)

    def test_partial_welcome_reply_does_not_mark_session(self):
        session = make_session(welcome_sent=False)
        reply = "Hola Jorge, ¿me compartes el año del vehículo?"

        self.assertFalse(helper.reply_contains_full_welcome(reply))
        updated = helper.mark_welcome_sent_on_session(
            session,
            helper.reply_contains_full_welcome(reply),
        )

        self.assertFalse(updated)
        self.assertFalse(session.welcome_sent)

    def test_year_after_partial_vehicle_is_preserved_and_asks_location(self):
        session = make_session(
            welcome_sent=True,
            step="ask_vehicle",
            customer_name="Jorge",
            vehicle_brand="Mazda",
            vehicle_model="3",
            vehicle_info="Mazda 3",
            last_message="2024",
        )

        next_step, should_send, reply, vals = apply_ai(
            session,
            {
                "intent": "progressive_data_capture",
                "vehicle_year": "2024",
                "next_required_field": "city",
                "assistant_message": "Perfecto Jorge. ¿En qué ciudad o barrio te encuentras?",
            },
        )

        self.assertEqual(next_step, "ask_location")
        self.assertTrue(should_send)
        self.assertEqual(session.customer_name, "Jorge")
        self.assertEqual(session.vehicle_brand, "Mazda")
        self.assertEqual(session.vehicle_model, "3")
        self.assertEqual(session.vehicle_year, "2024")

    def test_empty_ai_reply_uses_safe_fallback(self):
        session = make_session(last_message="Hola")

        next_step, should_send, reply, vals = apply_ai(
            session,
            {
                "intent": "progressive_data_capture",
                "next_required_field": "customer_name",
                "reply": None,
                "assistant_message": None,
            },
        )

        self.assertEqual(next_step, "ask_name")
        self.assertTrue(should_send)
        self.assertTrue(reply)
        self.assertIn("Bienvenido a Mega Baterías", reply)
        self.assertIn("Atendemos Medellín y Área Metropolitana", reply)
        self.assertIn("Horario: lunes a sábado de 7:00 a.m. a 6:00 p.m.", reply)
        self.assertIn("nombre", reply.lower())

    def test_first_reply_wraps_simple_name_question_with_full_welcome(self):
        session = make_session(
            welcome_sent=False,
            last_message="Hola vengo de la web",
        )

        next_step, should_send, reply, vals = apply_ai(
            session,
            {
                "intent": "progressive_data_capture",
                "next_required_field": "customer_name",
                "reply": "Con gusto te ayudo. ¿Me regalas por favor tu nombre?",
                "assistant_message": "Con gusto te ayudo. ¿Me regalas por favor tu nombre?",
            },
        )

        self.assertEqual(next_step, "ask_name")
        self.assertTrue(should_send)
        self.assertIn("Hola 👋 Bienvenido a Mega Baterías.", reply)
        self.assertIn("Atendemos Medellín y Área Metropolitana", reply)
        self.assertIn("carros, camionetas y camiones", reply)
        self.assertIn("¿Me regalas por favor tu nombre?", reply)
        self.assertTrue(helper.reply_contains_full_welcome(reply))

    def test_first_reply_with_detected_name_includes_summary_once(self):
        session = make_session(
            welcome_sent=False,
            last_message="Jorge",
        )

        next_step, should_send, reply, vals = apply_ai(
            session,
            {
                "intent": "progressive_data_capture",
                "customer_name": "Jorge",
                "next_required_field": "vehicle_brand",
                "reply": "¿Me compartes por favor la marca, línea y año del vehículo?",
                "assistant_message": "¿Me compartes por favor la marca, línea y año del vehículo?",
            },
        )

        self.assertEqual(next_step, "ask_vehicle")
        self.assertTrue(should_send)
        self.assertIn("Hola 👋 Bienvenido a Mega Baterías.", reply)
        self.assertIn("👤 Nombre: Jorge", reply)
        self.assertIn("marca, línea y año", reply)

    def test_welcome_sent_session_never_wraps_reply_again(self):
        session = make_session(
            welcome_sent=True,
            customer_name="Jorge",
            last_message="mazda 3 2023",
        )

        next_step, should_send, reply, vals = apply_ai(
            session,
            {
                "intent": "progressive_data_capture",
                "vehicle_brand": "mazda",
                "vehicle_model": "3",
                "vehicle_year": "2023",
                "next_required_field": "city",
                "reply": "Perfecto Jorge. ¿En qué ciudad o barrio te encuentras?",
                "assistant_message": "Perfecto Jorge. ¿En qué ciudad o barrio te encuentras?",
            },
        )

        self.assertEqual(next_step, "ask_location")
        self.assertTrue(should_send)
        self.assertNotIn("Bienvenido a Mega Baterías", reply)
        self.assertNotIn("Atendemos Medellín", reply)

    def test_mark_welcome_sent_only_when_message_was_sent(self):
        session = make_session(welcome_sent=False)

        updated = helper.mark_welcome_sent_on_session(session, False)
        self.assertFalse(updated)
        self.assertFalse(session.welcome_sent)

        updated = helper.mark_welcome_sent_on_session(session, True)
        self.assertTrue(updated)
        self.assertTrue(session.welcome_sent)

        updated = helper.mark_welcome_sent_on_session(session, True)
        self.assertFalse(updated)


if __name__ == "__main__":
    unittest.main()
