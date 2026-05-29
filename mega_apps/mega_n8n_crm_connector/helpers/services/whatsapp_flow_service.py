import logging
import os
from odoo.http import request  # type: ignore
from ...helpers.n8n_payload_helper import get_n8n_payload
from ...helpers.whatsapp_session_helper import (
    get_or_create_session,
    missing_phone_response,
    session_snapshot,
    is_terminal_step,
    parse_ai_result,
    get_active_session,
    whatsapp_response,
    build_ai_session_update,
    get_safe_reply,
    mark_welcome_sent_on_session,
    reply_contains_full_welcome,
)
from ...helpers.whatsapp_ai_prompt import get_ai_instruction
from ...helpers.whatsapp_messages import get_confirmation_message
from ...helpers.constants import NO_ACTIVE_SESSION_REPLY
from ...helpers.constants import (
    OLD_BATTERY_SURCHARGE,
    WOMPI_PRIVATE_KEY_ENV_NAMES,
    WOMPI_PRIVATE_KEY_PARAM_ALIASES,
)
from ...helpers.whatsapp_crm_helper import (
    create_or_update_lead_from_session
)
from ...helpers.whatsapp_catalog_helper import (
    build_recommended_battery_message_for_lead,
    build_more_battery_options_message_for_lead,
    get_battery_option_for_catalog_index,
    get_battery_option_price,
    get_battery_line_label,
    format_money,
)
from ...helpers.whatsapp_chatter_helper import (
    log_whatsapp_conversation_on_lead,
)
from ...helpers.whatsapp_chatter_helper import (
    log_customer_message_on_lead_from_session,
)
from ...helpers.wompi_payment_helper import create_wompi_payment_link

_logger = logging.getLogger(__name__)


def _get_wompi_private_key(env) -> str:
    Config = env["ir.config_parameter"].sudo()

    for param_name in WOMPI_PRIVATE_KEY_PARAM_ALIASES:
        private_key = (Config.get_param(param_name) or "").strip()
        if private_key:
            return private_key

    for env_name in WOMPI_PRIVATE_KEY_ENV_NAMES:
        private_key = (os.environ.get(env_name) or "").strip()
        if private_key:
            return private_key

    return ""


def _payment_fallback_reply(name: str | None) -> str:
    customer = name or "señor/a"
    return (
        f"Perfecto {customer}. Ya registramos tu interés en la batería recomendada. "
        "En este momento no fue posible generar el link de pago automáticamente, "
        "pero en breve un asesor de Mega Baterías continuará contigo para finalizar la compra. 🔋🚗"
    )


def _parse_selected_catalog_option(ai_result: dict, message: str | None) -> int:
    option_index = ai_result.get("selected_catalog_option") or ai_result.get("selected_option")

    try:
        option_index = int(option_index or 0)
    except (TypeError, ValueError):
        option_index = 0

    normalized_message = (message or "").lower()

    if option_index <= 0:
        stripped_message = normalized_message.strip()
        if stripped_message in {"1", "2", "3"}:
            option_index = int(stripped_message)

    if option_index <= 0:
        option_words = [
            (1, ("opcion 1", "opción 1", "la 1", "numero 1", "número 1")),
            (2, ("opcion 2", "opción 2", "la 2", "numero 2", "número 2")),
            (3, ("opcion 3", "opción 3", "la 3", "numero 3", "número 3")),
        ]
        for index, words in option_words:
            if any(word in normalized_message for word in words):
                option_index = index
                break

    if option_index <= 0:
        if "barata" in normalized_message or "economica" in normalized_message or "económica" in normalized_message:
            option_index = 1
        elif "mejor" in normalized_message:
            option_index = 1

    return max(1, min(option_index or 1, 3))


def _store_catalog_battery_on_session(env, session, lead, option_index: int = 1):
    option = False

    if lead:
        option = get_battery_option_for_catalog_index(env, lead, option_index)
        option = option[:1]

    if not option and session.selected_battery_option_id:
        option = session.selected_battery_option_id

    if not option:
        return False, 0.0

    price = get_battery_option_price(option)
    values = {
        "selected_battery_option_id": option.id,
        "selected_battery_price": price,
    }

    session.write(values)
    return option, price


def _build_price_without_old_battery_reply(session, option, base_price: float) -> str:
    customer = session.customer_name or "señor/a"
    final_value = float(base_price or 0) + OLD_BATTERY_SURCHARGE
    line_label = get_battery_line_label(option)

    return (
        f"Claro {customer} 👍\n\n"
        "Si deseas conservar la batería usada, el valor final sería:\n\n"
        f"🔋 Línea: {line_label}\n"
        f"📌 Referencia: {option.reference}\n"
        f"💰 Valor final: {format_money(final_value)} COP\n\n"
        f"Incluye recargo de {format_money(OLD_BATTERY_SURCHARGE)} por conservar la batería usada.\n\n"
        "Para continuar, respóndeme si aceptas esta opción o si prefieres hablar con un asesor."
    )


def _build_payment_success_reply(session, option, final_value: float, payment_url: str) -> str:
    customer = session.customer_name or "señor/a"
    line_label = get_battery_line_label(option)

    if session.customer_leaves_old_battery:
        used_battery_note = "El valor aplica entregando la batería usada."
    else:
        used_battery_note = (
            f"Incluye recargo de {format_money(OLD_BATTERY_SURCHARGE)} "
            "por conservar la batería usada."
        )

    return (
        f"Perfecto {customer} 👍\n\n"
        "Ya dejamos registrada tu solicitud:\n\n"
        f"🔋 Línea: {line_label}\n"
        f"📌 Referencia: {option.reference}\n"
        f"💰 Valor final: {format_money(final_value)} COP\n\n"
        f"{used_battery_note}\n\n"
        "Puedes realizar el pago seguro aquí 👇\n\n"
        f"{payment_url}\n\n"
        "Una vez confirmado el pago, un asesor de Mega Baterías continuará contigo "
        "para validar disponibilidad y coordinar el despacho. 🚗🔋"
    )


def _create_wompi_payment_response(env, session, lead, option_index: int = 1):
    option, base_price = _store_catalog_battery_on_session(
        env,
        session,
        lead,
        option_index=option_index,
    )

    if not option or base_price <= 0:
        _logger.warning(
            "Cannot create Wompi link: missing option or price session=%s option=%s price=%s",
            session.id,
            option.id if option else False,
            base_price,
        )
        session.write({"step": "advisor_handoff"})
        return "advisor_handoff", True, _payment_fallback_reply(session.customer_name)

    final_value = base_price
    if not session.customer_leaves_old_battery:
        final_value += OLD_BATTERY_SURCHARGE

    private_key = _get_wompi_private_key(env)
    if not private_key:
        _logger.warning(
            "Cannot create Wompi link: private key is not configured. "
            "Configure one ICP alias or env var. session=%s",
            session.id,
        )
        session.write({"step": "advisor_handoff"})
        return "advisor_handoff", True, _payment_fallback_reply(session.customer_name)

    customer = (session.customer_name or "").strip()
    payment_name = f"Mega Baterías - {customer} - {option.reference}" if customer else f"Mega Baterías - {option.reference}"

    payment = create_wompi_payment_link(
        private_key=private_key,
        name=payment_name,
        description=f"Batería {option.reference} para {session.vehicle_info or 'vehículo'}",
        amount=final_value,
        single_use=True,
        collect_shipping=False,
    )

    if not payment.get("success") or not payment.get("payment_url"):
        _logger.warning(
            "Wompi payment link failed for session=%s error=%s",
            session.id,
            payment.get("error"),
        )
        session.write({"step": "advisor_handoff"})
        return "advisor_handoff", True, _payment_fallback_reply(session.customer_name)

    session.write(
        {
            "wompi_payment_link_id": payment.get("payment_link_id"),
            "wompi_payment_url": payment.get("payment_url"),
            "step": "dispatch_requested",
        }
    )

    return (
        "dispatch_requested",
        True,
        _build_payment_success_reply(session, option, final_value, payment["payment_url"]),
    )


def _ensure_non_empty_reply(
    phone: str,
    step: str,
    should_send: bool,
    reply: str,
    ai_result: dict | None = None,
    session=None,
):
    if should_send and not (reply or "").strip():
        fallback_reply, used_fallback = get_safe_reply(
            ai_result or {},
            reply,
            session=session,
        )
        if used_fallback:
            _logger.warning(
                "Using fallback WhatsApp reply phone=%s session=%s step=%s",
                phone,
                getattr(session, "id", False),
                step,
            )
            return True, fallback_reply

        _logger.warning(
            "Avoiding empty WhatsApp reply phone=%s step=%s",
            phone,
            step,
        )
        return False, ""

    return should_send, reply


def mark_welcome_sent_from_payload(env, payload: dict) -> dict:
    phone = (payload.get("phone") or "").strip()
    message_sent = bool(payload.get("message_sent"))

    if not phone:
        return missing_phone_response(
            error="missing_phone",
            should_use_ai=False,
            should_send=False,
        )

    session = get_active_session(env, phone)

    if not session:
        return whatsapp_response(
            False,
            "error",
            NO_ACTIVE_SESSION_REPLY,
            should_send=False,
            kind="no_active_session",
        )

    updated = mark_welcome_sent_on_session(session, message_sent)

    return whatsapp_response(
        True,
        session.step,
        "",
        should_send=False,
        kind="welcome_sent_marked" if updated else "welcome_sent_unchanged",
        welcome_sent=bool(getattr(session, "welcome_sent", False)),
        session=session_snapshot(session),
    )


def build_ai_context_response(self, **post):
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
            _logger.info("\n\n\n Primer mensaje se enviara a IA para captura progresiva \n\n\n")
            return {
                "success": True,
                "should_use_ai": True,
                "should_send": False,
                "kind": "ai_context",
                "phone": session.phone,
                "phone_number_id": session.phone_number_id,
                "step": session.step,
                "welcome_sent": bool(getattr(session, "welcome_sent", False)),
                "customer_name": session.customer_name or "",
                "vehicle_brand": getattr(session, "vehicle_brand", "") or "",
                "vehicle_model": getattr(session, "vehicle_model", "") or "",
                "vehicle_year": getattr(session, "vehicle_year", "") or "",
                "vehicle_info": session.vehicle_info or "",
                "city": getattr(session, "city", "") or "",
                "neighborhood": getattr(session, "neighborhood", "") or "",
                "location": session.location or "",
                "plate": getattr(session, "plate", "") or "",
                "last_message": message,
                "ai_instruction": get_ai_instruction(session, message),
                "session": session_snapshot(session),
            }

        if is_terminal_step(session.step):
            return {
                "success": True,
                "should_use_ai": False,
                "should_send": False,
                "kind": "terminal_session",
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
            "welcome_sent": bool(getattr(session, "welcome_sent", False)),
            "customer_name": session.customer_name or "",
            "vehicle_brand": getattr(session, "vehicle_brand", "") or "",
            "vehicle_model": getattr(session, "vehicle_model", "") or "",
            "vehicle_year": getattr(session, "vehicle_year", "") or "",
            "vehicle_info": session.vehicle_info or "",
            "city": getattr(session, "city", "") or "",
            "neighborhood": getattr(session, "neighborhood", "") or "",
            "location": session.location or "",
            "plate": getattr(session, "plate", "") or "",
            "last_message": message,
            "ai_instruction": get_ai_instruction(session, message),
            "session": session_snapshot(session),
        }

def apply_ai_to_whatsapp_session(self, **post):
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

    ai_result_for_lead = {
        **ai_result,
        "vehicle_brand": getattr(session, "vehicle_brand", "") or ai_result.get("vehicle_brand") or "",
        "vehicle_model": getattr(session, "vehicle_model", "") or ai_result.get("vehicle_model") or "",
        "vehicle_year": getattr(session, "vehicle_year", "") or ai_result.get("vehicle_year") or "",
        "location": session.location or ai_result.get("location") or "",
    }

    # lead = create_or_update_lead_from_session(request.env, session)
    lead = create_or_update_lead_from_session(
        request.env,
        session,
        ai_result=ai_result_for_lead,
    )

    if next_step == "catalog_sent" and lead:
        option, base_price = _store_catalog_battery_on_session(
            request.env,
            session,
            lead,
            option_index=1,
        )

        if option and base_price > 0:
            if ai_result.get("intent") == "ask_price_without_old_battery":
                reply = _build_price_without_old_battery_reply(
                    session,
                    option,
                    base_price,
                )
            else:
                session.write({"customer_leaves_old_battery": True})
                reply = build_recommended_battery_message_for_lead(request.env, lead)
            should_send = True
        else:
            if option:
                reply = _payment_fallback_reply(session.customer_name)
            else:
                reply = build_more_battery_options_message_for_lead(request.env, lead)
            should_send = True
            session.write({"step": "advisor_handoff"})


    if next_step == "confirm_data":
        reply = get_confirmation_message(session)
        should_send = True

    if next_step in {"more_options_sent", "more_catalog_sent"} and lead:
        if ai_result.get("intent") == "ask_price_without_old_battery" and not reply:
            option_index = _parse_selected_catalog_option(
                ai_result,
                session.last_message,
            )
            option, base_price = _store_catalog_battery_on_session(
                request.env,
                session,
                lead,
                option_index=option_index,
            )
            if option and base_price > 0:
                reply = _build_price_without_old_battery_reply(
                    session,
                    option,
                    base_price,
                )
            else:
                reply = (
                    "Para darte el valor exacto, dime cuál opción prefieres: "
                    "opción 1, opción 2 u opción 3. 🔋🚗"
                )
        else:
            reply = build_more_battery_options_message_for_lead(request.env, lead)
        should_send = True
        if session.step != "more_catalog_sent":
            session.write({"step": "more_catalog_sent"})

    if next_step == "payment_link_sent":
        option_index = 1
        if session.step in {"more_options_sent", "more_catalog_sent", "payment_link_sent"}:
            option_index = _parse_selected_catalog_option(
                ai_result,
                session.last_message,
            )

        next_step, should_send, reply = _create_wompi_payment_response(
            request.env,
            session,
            lead,
            option_index=option_index,
        )

    should_send, reply = _ensure_non_empty_reply(
        phone,
        session.step,
        should_send,
        reply,
        ai_result=ai_result,
        session=session,
    )

    if should_send and reply_contains_full_welcome(reply):
        updated_welcome = mark_welcome_sent_on_session(session, True)
        if updated_welcome:
            _logger.info(
                "Marked welcome_sent after generating welcome reply phone=%s session=%s",
                phone,
                session.id,
            )

    if lead:
        log_whatsapp_conversation_on_lead(
            lead,
            customer_message=session.last_message,
            bot_reply=reply if should_send else "",
        )

    return whatsapp_response(
        True,
        session.step,
        reply,
        should_send=should_send,
        session=session_snapshot(session),
        lead_id=lead.id if lead else False,
    )


def mark_welcome_sent_after_send(self, **post):
        payload = get_n8n_payload()
        return mark_welcome_sent_from_payload(request.env, payload)

def log_terminal_whatsapp_message(self):
        payload = get_n8n_payload()

        phone = (payload.get("phone") or "").strip()
        message = (payload.get("message") or "").strip()
        message_id = (payload.get("message_id") or "").strip()

        _logger.info(
            "N8N WhatsApp log message phone=%s message_id=%s",
            phone,
            message_id,
        )

        if not phone:
            return missing_phone_response(
                error="missing_phone",
                should_use_ai=False,
                should_send=False,
            )

        session = get_active_session(request.env, phone)

        if not session:
            return whatsapp_response(
                False,
                "error",
                "No encontré una sesión activa para registrar el mensaje.",
                should_send=False,
                should_use_ai=False,
                kind="no_active_session",
            )

        # Seguridad: aunque n8n ya validó el IF, Odoo vuelve a validar.
        if not is_terminal_step(session.step):
            return whatsapp_response(
                True,
                session.step,
                "",
                should_send=False,
                should_use_ai=False,
                kind="ignored_not_terminal_session",
                session=session_snapshot(session),
            )

        # Este es el punto clave:
        # NO buscamos otro lead por teléfono.
        # El lead correcto es el vinculado a la sesión activa.
        if not session.lead_id:
            return whatsapp_response(
                False,
                session.step,
                "",
                should_send=False,
                should_use_ai=False,
                kind="session_without_lead",
                session=session_snapshot(session),
            )

        logged = log_customer_message_on_lead_from_session(
            session,
            message=message,
            message_id=message_id,
        )

        return whatsapp_response(
            True,
            session.step,
            "",
            should_send=False,
            should_use_ai=False,
            kind="message_logged" if logged else "message_not_logged",
            logged=logged,
            lead_id=session.lead_id.id,
            session=session_snapshot(session),
        )
