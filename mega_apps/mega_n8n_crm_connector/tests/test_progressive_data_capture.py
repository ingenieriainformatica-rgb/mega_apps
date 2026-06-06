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
    package = sys.modules.setdefault(PACKAGE_ROOT, types.ModuleType(PACKAGE_ROOT))
    package.__path__ = [str(HELPERS_DIR.parent)]
    helpers_package = sys.modules.setdefault(HELPERS_PACKAGE, types.ModuleType(HELPERS_PACKAGE))
    helpers_package.__path__ = [str(HELPERS_DIR)]

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
        "whatsapp_business_hours_helper",
        "whatsapp_vehicle_helper",
        "whatsapp_session_helper",
        "whatsapp_ai_prompt",
    ):
        _load_helper_module(module_name)
    return sys.modules[f"{HELPERS_PACKAGE}.whatsapp_session_helper"]


def _load_catalog_helper():
    _install_odoo_stub()
    for module_name in (
        "constants",
        "whatsapp_catalog_helper",
    ):
        _load_helper_module(module_name)
    return sys.modules[f"{HELPERS_PACKAGE}.whatsapp_catalog_helper"]


def _load_crm_helper():
    _install_odoo_stub()
    for module_name in (
        "constants",
        "whatsapp_business_hours_helper",
        "whatsapp_vehicle_helper",
        "whatsapp_crm_helper",
    ):
        _load_helper_module(module_name)
    return sys.modules[f"{HELPERS_PACKAGE}.whatsapp_crm_helper"]


helper = _load_progressive_helper()
prompt = sys.modules[f"{HELPERS_PACKAGE}.whatsapp_ai_prompt"]
business_hours_helper = sys.modules[f"{HELPERS_PACKAGE}.whatsapp_business_hours_helper"]
catalog_helper = _load_catalog_helper()
crm_helper = _load_crm_helper()


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
        "coverage_status": True,
        "plate": True,
        "battery_request": True,
        "relevant_data": True,
        "conversation_summary": True,
        "welcome_sent": True,
        "is_after_hours": True,
        "after_hours_accepted": True,
    }

    def write(self, values):
        for key, value in values.items():
            setattr(self, key, value)


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
        "coverage_status": "not_provided",
        "plate": "",
        "battery_request": False,
        "relevant_data": "",
        "conversation_summary": "",
        "welcome_sent": False,
        "is_after_hours": False,
        "after_hours_accepted": False,
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


def apply_simple_ai(session, ai_result):
    next_step, should_send, reply, vals = helper.build_simple_ai_session_update(
        session,
        ai_result,
    )
    for key, value in vals.items():
        setattr(session, key, value)
    return next_step, should_send, reply, vals


def apply_after_hours_ai(session, ai_result):
    next_step, should_send, reply, vals = helper.build_after_hours_ai_session_update(
        session,
        ai_result,
    )
    for key, value in vals.items():
        setattr(session, key, value)
    return next_step, should_send, reply, vals


class TestProgressiveDataCapture(unittest.TestCase):
    def test_business_hours_sunday_is_always_closed(self):
        from datetime import datetime

        now = datetime(2026, 6, 7, 12, 0, tzinfo=helper.COLOMBIA_TZ)

        self.assertFalse(business_hours_helper.is_business_hours(now))

    def test_business_hours_before_6_is_closed(self):
        from datetime import datetime

        now = datetime(2026, 6, 1, 5, 59, tzinfo=helper.COLOMBIA_TZ)

        self.assertFalse(business_hours_helper.is_business_hours(now))

    def test_business_hours_at_6_is_open(self):
        from datetime import datetime

        now = datetime(2026, 6, 1, 6, 0, tzinfo=helper.COLOMBIA_TZ)

        self.assertTrue(business_hours_helper.is_business_hours(now))

    def test_business_hours_before_19_is_open(self):
        from datetime import datetime

        now = datetime(2026, 6, 1, 18, 59, tzinfo=helper.COLOMBIA_TZ)

        self.assertTrue(business_hours_helper.is_business_hours(now))

    def test_business_hours_at_19_is_closed(self):
        from datetime import datetime

        now = datetime(2026, 6, 1, 19, 0, tzinfo=helper.COLOMBIA_TZ)

        self.assertFalse(business_hours_helper.is_business_hours(now))

    def test_after_hours_with_complete_data_goes_to_handoff(self):
        session = make_session(
            is_after_hours=True,
            last_message="Sí, soy Laura, estoy en Envigado y tengo un Mazda 3 2020",
        )

        next_step, should_send, reply, vals = apply_after_hours_ai(
            session,
            {
                "intent": "after_hours_data_capture",
                "after_hours_accepted": True,
                "customer_name": "Laura",
                "location": "Envigado",
                "vehicle_brand": "Mazda",
                "vehicle_model": "3",
                "vehicle_year": "2020",
            },
        )

        self.assertEqual(next_step, "after_hours_handoff")
        self.assertTrue(should_send)
        self.assertTrue(vals["is_after_hours"])
        self.assertTrue(vals["after_hours_accepted"])
        self.assertEqual(vals["vehicle_brand"], "Mazda")
        self.assertEqual(vals["vehicle_model"], "3")
        self.assertEqual(vals["vehicle_year"], "2020")
        self.assertIn("retome el horario", reply.lower())

    def test_after_hours_decline_closes_without_repeating_schedule(self):
        session = make_session(
            is_after_hours=True,
            last_message="no",
        )

        next_step, should_send, reply, vals = apply_after_hours_ai(
            session,
            {
                "intent": "after_hours_data_capture",
                "after_hours_accepted": False,
            },
        )

        self.assertEqual(next_step, "advisor_handoff")
        self.assertTrue(should_send)
        self.assertTrue(vals["is_after_hours"])
        self.assertFalse(vals["after_hours_accepted"])
        self.assertIn("gracias por escribirnos", reply.lower())
        self.assertNotIn("deseas dejarlos", reply.lower())

    def test_after_hours_out_of_coverage_does_not_ask_vehicle(self):
        session = make_session(
            is_after_hours=True,
            customer_name="Jorge",
            last_message="bogota",
        )

        next_step, should_send, reply, vals = apply_after_hours_ai(
            session,
            {
                "intent": "after_hours_data_capture",
                "after_hours_accepted": True,
                "location": "bogota",
            },
        )

        self.assertEqual(next_step, "out_of_coverage")
        self.assertTrue(should_send)
        self.assertEqual(vals["location"], "bogota")
        self.assertIn("medellín", reply.lower())
        self.assertIn("área metropolitana", reply.lower())
        self.assertNotIn("qué vehículo", reply.lower())

    def test_after_hours_corrects_msda_to_mazda(self):
        session = make_session(
            is_after_hours=True,
            customer_name="Jorge",
            location="Envigado",
            last_message="msda 3 2023",
        )

        next_step, should_send, reply, vals = apply_after_hours_ai(
            session,
            {
                "intent": "after_hours_data_capture",
                "after_hours_accepted": True,
            },
        )

        self.assertEqual(next_step, "after_hours_handoff")
        self.assertTrue(should_send)
        self.assertEqual(vals["vehicle_brand"], "Mazda")
        self.assertEqual(vals["vehicle_model"], "3")
        self.assertEqual(vals["vehicle_year"], "2023")
        self.assertIn("Mazda 3 2023", reply)

    def test_complete_qualified_session_sets_priority_three(self):
        session = make_session(
            customer_name="Laura",
            location="Envigado",
            vehicle_brand="Mazda",
            vehicle_model="3",
            vehicle_year="2020",
        )
        Lead = types.SimpleNamespace(_fields={"priority": True})
        values = {}

        crm_helper.apply_qualified_lead_priority(Lead, values, session)

        self.assertEqual(values["priority"], "3")

    def test_incomplete_session_does_not_set_priority(self):
        session = make_session(
            customer_name="Laura",
            location="Envigado",
            vehicle_brand="Mazda",
        )
        Lead = types.SimpleNamespace(_fields={"priority": True})
        values = {}

        crm_helper.apply_qualified_lead_priority(Lead, values, session)

        self.assertNotIn("priority", values)

    def test_out_of_coverage_session_does_not_set_priority(self):
        session = make_session(
            customer_name="Laura",
            location="Bogota",
            vehicle_brand="Mazda",
            vehicle_model="3",
            vehicle_year="2020",
        )
        Lead = types.SimpleNamespace(_fields={"priority": True})
        values = {}

        crm_helper.apply_qualified_lead_priority(Lead, values, session)

        self.assertNotIn("priority", values)

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

    def test_simple_flow_initial_message_asks_only_name(self):
        session = make_session(last_message="Hola")

        next_step, should_send, reply, vals = apply_simple_ai(
            session,
            {
                "intent": "simple_data_capture",
                "assistant_message": "¿En qué barrio estás?",
            },
        )

        self.assertEqual(next_step, "ask_name")
        self.assertTrue(should_send)
        self.assertNotIn("customer_name", vals)
        self.assertIn("nombre", reply.lower())
        self.assertIn("moisés castrillón", reply.lower())
        self.assertNotIn("presupuesto", reply.lower())
        self.assertNotIn("marca", reply.lower())
        self.assertNotIn("placa", reply.lower())
        self.assertNotIn("barrio", reply.lower())

    def test_simple_flow_with_vehicle_but_no_name_summarizes_and_asks_name(self):
        session = make_session(last_message="Tengo un Mazda 3 2020")

        next_step, should_send, reply, vals = apply_simple_ai(
            session,
            {
                "intent": "simple_data_capture",
                "vehicle_brand": "Mazda",
                "vehicle_model": "3",
                "vehicle_year": "2020",
            },
        )

        self.assertEqual(next_step, "ask_name")
        self.assertTrue(should_send)
        self.assertEqual(vals["vehicle_brand"], "Mazda")
        self.assertEqual(vals["vehicle_model"], "3")
        self.assertEqual(vals["vehicle_year"], "2020")
        self.assertIn("tengo tu mazda 3 2020", reply.lower())
        self.assertIn("mazda", reply.lower())
        self.assertIn("nombre", reply.lower())
        self.assertNotIn("medellín", reply.lower())

    def test_simple_flow_asks_location_after_name(self):
        session = make_session(last_message="Soy Laura")

        next_step, should_send, reply, vals = apply_simple_ai(
            session,
            {
                "intent": "simple_data_capture",
                "customer_name": "Laura",
                "assistant_message": "Dame la placa.",
            },
        )

        self.assertEqual(next_step, "ask_location")
        self.assertTrue(should_send)
        self.assertEqual(vals["customer_name"], "Laura")
        self.assertIn("medellín", reply.lower())
        self.assertIn("municipio cercano", reply.lower())
        self.assertNotIn("placa", reply.lower())

    def test_simple_flow_with_name_and_vehicle_summarizes_and_asks_location(self):
        session = make_session(last_message="Soy Jorge, tengo un Mazda 3 2020")

        next_step, should_send, reply, vals = apply_simple_ai(
            session,
            {
                "intent": "simple_data_capture",
                "customer_name": "Jorge",
                "vehicle_brand": "Mazda",
                "vehicle_model": "3",
                "vehicle_year": "2020",
            },
        )

        self.assertEqual(next_step, "ask_location")
        self.assertTrue(should_send)
        self.assertEqual(vals["customer_name"], "Jorge")
        self.assertEqual(vals["vehicle_brand"], "Mazda")
        self.assertEqual(vals["vehicle_model"], "3")
        self.assertEqual(vals["vehicle_year"], "2020")
        self.assertNotIn("hasta ahora tengo", reply.lower())
        self.assertNotIn("mazda", reply.lower())
        self.assertIn("medellín", reply.lower())

    def test_simple_flow_extracts_out_of_coverage_location_from_message(self):
        session = make_session(
            customer_name="Jorge",
            step="ask_location",
            last_message="en bogota",
        )

        next_step, should_send, reply, vals = apply_simple_ai(
            session,
            {
                "intent": "simple_data_capture",
                "assistant_message": "¿Estás en Medellín?",
            },
        )

        self.assertEqual(next_step, "out_of_coverage")
        self.assertTrue(should_send)
        self.assertEqual(vals["location"], "bogota")
        self.assertNotIn("municipio cercano", reply.lower())

    def test_simple_flow_blocks_known_out_of_coverage_cities(self):
        cases = [
            "Estoy en Cartagena",
            "Estoy en Cali",
            "Estoy en Barranquilla",
            "Estoy en Pereira",
            "Estoy en Rionegro",
        ]

        for message in cases:
            with self.subTest(message=message):
                session = make_session(
                    customer_name="Jorge",
                    step="ask_location",
                    last_message=message,
                )

                next_step, should_send, reply, vals = apply_simple_ai(
                    session,
                    {
                        "intent": "simple_data_capture",
                        "assistant_message": "¿Estás en Medellín?",
                    },
                )

                self.assertEqual(next_step, "out_of_coverage")
                self.assertTrue(should_send)
                self.assertTrue(vals["location"])
                self.assertNotIn("nombre", reply.lower())
                self.assertNotIn("marca", reply.lower())
                self.assertNotIn("modelo", reply.lower())
                self.assertNotIn("año", reply.lower())

    def test_simple_flow_allows_confirmed_covered_locations(self):
        cases = [
            ("Estoy en Castilla", "Castilla"),
            ("Estoy en Itagüí", "Itagüí"),
        ]

        for message, expected_location in cases:
            with self.subTest(message=message):
                session = make_session(last_message=message)

                next_step, should_send, reply, vals = apply_simple_ai(
                    session,
                    {
                        "intent": "simple_data_capture",
                        "assistant_message": "",
                    },
                )

                self.assertEqual(next_step, "ask_name")
                self.assertTrue(should_send)
                self.assertEqual(vals["location"], expected_location)
                self.assertIn("baterías", reply.lower())

    def test_simple_flow_confirms_pending_ambiguous_location_with_medellin(self):
        session = make_session(last_message="la colinita")

        next_step, should_send, reply, vals = apply_simple_ai(
            session,
            {
                "intent": "simple_data_capture",
                "assistant_message": "",
            },
        )

        self.assertEqual(next_step, "ask_location")
        self.assertTrue(should_send)
        self.assertEqual(vals["location"], "la colinita")
        self.assertEqual(reply, helper.AMBIGUOUS_COVERAGE_REPLY)

        session.write(vals)
        session.last_message = "en medellin"

        next_step, should_send, reply, vals = apply_simple_ai(
            session,
            {
                "intent": "simple_data_capture",
                "assistant_message": "",
            },
        )

        self.assertEqual(next_step, "ask_name")
        self.assertTrue(should_send)
        self.assertEqual(vals["city"], "Medellín")
        self.assertEqual(vals["location"], "la colinita")
        self.assertNotEqual(reply, helper.AMBIGUOUS_COVERAGE_REPLY)

    def test_simple_flow_confirms_pending_centro_with_yes_in_medellin(self):
        session = make_session(last_message="centro")

        next_step, should_send, reply, vals = apply_simple_ai(
            session,
            {
                "intent": "simple_data_capture",
                "assistant_message": "",
            },
        )

        self.assertEqual(next_step, "ask_location")
        self.assertTrue(should_send)
        self.assertEqual(vals["location"], "centro")
        self.assertEqual(reply, helper.AMBIGUOUS_COVERAGE_REPLY)

        session.write(vals)
        session.last_message = "sí, en Medellín"

        next_step, should_send, reply, vals = apply_simple_ai(
            session,
            {
                "intent": "simple_data_capture",
                "assistant_message": "",
            },
        )

        self.assertEqual(next_step, "ask_name")
        self.assertTrue(should_send)
        self.assertEqual(vals["city"], "Medellín")
        self.assertEqual(vals["location"], "centro")
        self.assertNotEqual(reply, helper.AMBIGUOUS_COVERAGE_REPLY)

    def test_simple_flow_preserves_confirmed_coverage_after_vehicle_message(self):
        session = make_session(
            customer_name="Jorge",
            step="ask_location",
            location="itagui",
            coverage_status="ambiguous",
            last_message="si queda en medellin",
        )

        next_step, should_send, reply, vals = apply_simple_ai(
            session,
            {
                "intent": "simple_data_capture",
                "assistant_message": "",
            },
        )

        self.assertEqual(next_step, "ask_vehicle")
        self.assertTrue(should_send)
        self.assertEqual(vals["city"], "Medellín")
        self.assertEqual(vals["location"], "itagui")
        self.assertEqual(vals["coverage_status"], "covered")
        self.assertNotEqual(reply, helper.AMBIGUOUS_COVERAGE_REPLY)

        session.write(vals)
        session.last_message = "mazda 3 2017"

        next_step, should_send, reply, vals = apply_simple_ai(
            session,
            {
                "intent": "simple_data_capture",
                "vehicle_brand": "Mazda",
                "vehicle_model": "3",
                "vehicle_year": "2017",
                "assistant_message": "",
            },
        )

        self.assertNotEqual(next_step, "ask_location")
        self.assertTrue(should_send)
        self.assertEqual(vals["location"], "itagui")
        self.assertEqual(vals["coverage_status"], "covered")
        self.assertNotEqual(reply, helper.AMBIGUOUS_COVERAGE_REPLY)

    def test_simple_flow_asks_vehicle_after_location(self):
        session = make_session(
            customer_name="Laura",
            last_message="Estoy en Medellin",
        )

        next_step, should_send, reply, vals = apply_simple_ai(
            session,
            {
                "intent": "simple_data_capture",
                "location": "Medellin",
                "assistant_message": "¿Qué precio buscas?",
            },
        )

        self.assertEqual(next_step, "ask_vehicle")
        self.assertTrue(should_send)
        self.assertEqual(vals["location"], "Medellin")
        self.assertIn("qué carro manejas", reply.lower())
        self.assertIn("marca", reply.lower())
        self.assertIn("línea/modelo", reply.lower())

    def test_simple_flow_asks_only_missing_vehicle_field(self):
        session = make_session(
            customer_name="Laura",
            location="Medellin",
            vehicle_brand="Mazda",
            vehicle_model="3",
            last_message="Mazda 3",
        )

        next_step, should_send, reply, vals = apply_simple_ai(
            session,
            {
                "intent": "simple_data_capture",
                "assistant_message": "Listo, ya casi.",
            },
        )

        self.assertEqual(next_step, "ask_vehicle")
        self.assertTrue(should_send)
        self.assertIn("año", reply.lower())
        self.assertNotIn("marca, línea/modelo y año", reply.lower())

    def test_simple_flow_corrects_misspelled_vehicle_from_message(self):
        session = make_session(
            customer_name="Jorge",
            location="Envigado",
            last_message="masda 3 2023",
        )

        next_step, should_send, reply, vals = apply_simple_ai(
            session,
            {
                "intent": "simple_data_capture",
                "assistant_message": "¿Qué carro manejas?",
            },
        )

        self.assertEqual(next_step, "advisor_handoff")
        self.assertTrue(should_send)
        self.assertEqual(vals["vehicle_brand"], "Mazda")
        self.assertEqual(vals["vehicle_model"], "3")
        self.assertEqual(vals["vehicle_year"], "2023")
        self.assertIn("Mazda", reply)
        self.assertIn("asesor", reply.lower())

    def test_simple_flow_does_not_use_name_as_vehicle_model(self):
        session = make_session(last_message="Jorge y tengo un chebrolet")

        next_step, should_send, reply, vals = apply_simple_ai(
            session,
            {
                "intent": "simple_data_capture",
                "customer_name": "Jorge",
                "vehicle_brand": "chebrolet",
                "vehicle_model": "jorge y",
                "assistant_message": "¿Dónde estás?",
            },
        )

        self.assertEqual(next_step, "ask_location")
        self.assertTrue(should_send)
        self.assertEqual(vals["customer_name"], "Jorge")
        self.assertEqual(vals["vehicle_brand"], "Chevrolet")
        self.assertNotIn("vehicle_model", vals)
        self.assertNotIn("hasta ahora tengo", reply.lower())
        self.assertIn("medellín", reply.lower())
        self.assertNotIn("jorge y", reply.lower())

    def test_simple_flow_hands_off_to_advisor_with_minimum_data(self):
        session = make_session(last_message="Soy Laura, Mazda 3 2020 placa ABC123")

        next_step, should_send, reply, vals = apply_simple_ai(
            session,
            {
                "intent": "simple_data_capture",
                "customer_name": "Laura",
                "location": "Medellin",
                "vehicle_brand": "Mazda",
                "vehicle_model": "3",
                "vehicle_year": "2020",
                "plate": "ABC123",
                "assistant_message": "Confirma tus datos.",
            },
        )

        self.assertEqual(next_step, "advisor_handoff")
        self.assertTrue(should_send)
        self.assertEqual(vals["customer_name"], "Laura")
        self.assertEqual(vals["location"], "Medellin")
        self.assertEqual(vals["vehicle_brand"], "Mazda")
        self.assertEqual(vals["vehicle_model"], "3")
        self.assertEqual(vals["vehicle_year"], "2020")
        self.assertEqual(vals["plate"], "ABC123")
        self.assertIn("asesor", reply.lower())
        self.assertNotIn("confirma", reply.lower())

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

    def test_catalog_selection_uses_last_more_options_in_session(self):
        class FakeOption(types.SimpleNamespace):
            sale_price = 100000
            min_sale_price = 0
            max_sale_price = 0
            battery_line = "Gold"
            description = ""

        class FakeRecordSet(list):
            def __getitem__(self, item):
                value = super().__getitem__(item)
                if isinstance(item, slice):
                    return FakeRecordSet(value)
                return value

        class FakeOptionModel:
            def __init__(self, options_by_id):
                self.options_by_id = options_by_id

            def sudo(self):
                return self

            def browse(self, option_ids=None):
                option_ids = option_ids or []
                return FakeRecordSet(
                    self.options_by_id[option_id]
                    for option_id in option_ids
                    if option_id in self.options_by_id
                )

        class FakeEnv:
            def __init__(self, options_by_id):
                self.options_by_id = options_by_id

            def __getitem__(self, model_name):
                if model_name != "mega.battery.application.option":
                    raise AssertionError(model_name)
                return FakeOptionModel(self.options_by_id)

        option_a = FakeOption(id=101, reference="A")
        option_b = FakeOption(id=202, reference="B")
        option_c = FakeOption(id=203, reference="C")
        option_d = FakeOption(id=204, reference="D")
        options_by_id = {
            option.id: option
            for option in (option_a, option_b, option_c, option_d)
        }

        env = FakeEnv(options_by_id)
        lead = types.SimpleNamespace(
            contact_name="Jorge",
            partner_id=types.SimpleNamespace(name="Jorge"),
        )
        session = make_session(step="catalog_sent")

        original_find = catalog_helper.find_battery_options_for_lead
        try:
            def fake_find(_env, _lead, limit=3):
                if limit == 1:
                    return FakeRecordSet([option_a])
                if limit == 20:
                    return FakeRecordSet([option_a, option_b, option_c, option_d])
                return FakeRecordSet([option_a])

            catalog_helper.find_battery_options_for_lead = fake_find
            catalog_helper.build_recommended_battery_message_for_lead(
                env,
                lead,
                session=session,
            )
            self.assertEqual(session.last_catalog_option_ids, "101")

            catalog_helper.build_more_battery_options_message_for_lead(
                env,
                lead,
                session=session,
            )
            self.assertEqual(session.last_catalog_option_ids, "202,203,204")
            self.assertEqual(session.last_catalog_type, "more_options")

            def fail_if_recalculated(*_args, **_kwargs):
                raise AssertionError("catalog should not be recalculated")

            catalog_helper.find_battery_options_for_lead = fail_if_recalculated
            selected = catalog_helper.get_battery_option_for_catalog_index(
                env,
                lead,
                option_index=1,
                session=session,
            )
        finally:
            catalog_helper.find_battery_options_for_lead = original_find

        self.assertEqual(selected[0].reference, "B")


if __name__ == "__main__":
    unittest.main()
