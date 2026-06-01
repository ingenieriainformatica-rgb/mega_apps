import logging
from textwrap import dedent
import random

from odoo import fields  # type: ignore

from .constants import (
    LEAD_YEAR_FIELD,
    LEAD_BRAND_FIELD,
    LEAD_MODEL_FIELD
)


_logger = logging.getLogger(__name__)


def get_lead_vehicle_year(lead) -> int | None:
    if LEAD_YEAR_FIELD not in lead._fields:
        return None

    year_value = lead[LEAD_YEAR_FIELD]

    if not year_value:
        return None

    field = lead._fields[LEAD_YEAR_FIELD]

    if field.type == "integer":
        return int(year_value)

    if field.type == "char" and str(year_value).isdigit():
        return int(year_value)

    if field.type == "many2one":
        if "year" in year_value._fields and year_value.year:
            return int(year_value.year)
        if "name" in year_value._fields and str(year_value.name).isdigit():
            return int(year_value.name)

    return None


def find_battery_options_for_lead(env, lead, limit: int = 3):
    if not lead:
        return env["mega.battery.application.option"].sudo().browse()

    brand = lead[LEAD_BRAND_FIELD] if LEAD_BRAND_FIELD in lead._fields else False
    model = lead[LEAD_MODEL_FIELD] if LEAD_MODEL_FIELD in lead._fields else False
    vehicle_year = get_lead_vehicle_year(lead)

    if not brand or not model or not vehicle_year:
        _logger.info(
            "BATTERY CATALOG skipped lead=%s brand=%s model=%s year=%s",
            lead.id,
            brand.id if brand else False,
            model.id if model else False,
            vehicle_year,
        )
        return env["mega.battery.application.option"].sudo().browse()

    Application = env["mega.battery.application"].sudo()

    applications = Application.search(
        [
            ("active", "=", True),
            ("brand_id", "=", brand.id),
            ("model_id", "=", model.id),
            "|",
                ("year_from", "=", False),
                ("year_from", "<=", vehicle_year),
            "|",
                ("year_to", "=", False),
                ("year_to", ">=", vehicle_year),
        ],
        limit=10,
    )

    options = applications.mapped("option_ids").filtered(
        lambda option: option.sale_price or option.min_sale_price or option.max_sale_price
    )

    if not options:
        options = applications.mapped("option_ids")

    return options.sorted(
        key=lambda option: (
            not bool(option.sale_price),
            not bool(getattr(option, "whatsapp_recommended", False)),
            0 if "gold" in (option.battery_line or "").lower() else 1,
            option.option_number or 99,
            -(option.sale_price or 0),
        )
    )[:limit]


def format_money(value) -> str:
    value = float(value or 0)
    return "${:,.0f}".format(value).replace(",", ".")


def get_battery_option_price(option) -> float:
    if not option:
        return 0.0

    return float(
        option.sale_price
        or option.min_sale_price
        or option.max_sale_price
        or 0.0
    )


def get_battery_line_label(option) -> str:
    if not option:
        return ""

    if hasattr(option, "_get_battery_line_label"):
        return option._get_battery_line_label()

    return option.battery_line or ""


def _store_last_catalog_options_on_session(session, options, catalog_type: str) -> None:
    if not session:
        return

    option_ids = [str(option.id) for option in options if getattr(option, "id", False)]
    values = {
        "last_catalog_option_ids": ",".join(option_ids),
        "last_catalog_type": catalog_type,
        "last_catalog_sent_at": fields.Datetime.now(),
    }

    if hasattr(session, "write"):
        session.write(values)
    else:
        for key, value in values.items():
            setattr(session, key, value)


def _get_session_catalog_options(env, session, option_index: int):
    if not session:
        return None

    raw_option_ids = (getattr(session, "last_catalog_option_ids", "") or "").strip()
    if not raw_option_ids:
        return None

    Option = env["mega.battery.application.option"].sudo()

    option_ids = []
    for raw_option_id in raw_option_ids.split(","):
        raw_option_id = raw_option_id.strip()
        if not raw_option_id:
            continue
        try:
            option_ids.append(int(raw_option_id))
        except ValueError:
            _logger.warning(
                "Ignoring invalid saved catalog option id=%s session=%s",
                raw_option_id,
                getattr(session, "id", False),
            )

    if not option_ids or option_index > len(option_ids):
        return Option.browse()

    selected_option_id = option_ids[option_index - 1]
    return Option.browse([selected_option_id])


def build_battery_catalog_message_for_lead(env, lead, session=None) -> str:
    options = find_battery_options_for_lead(env, lead, limit=3)
    customer = lead.contact_name or lead.partner_id.name or "señor/a"
    vehicle = lead.vehicle_info if "vehicle_info" in lead._fields else False

    if not vehicle:
        vehicle = lead.display_name

    if not options:
        messages = [
            f"""
            Perfecto {customer} 👍

            Ya validamos los datos de tu vehículo. En este momento no encontré una referencia automática en el catálogo, pero un asesor de Mega Baterías revisará manualmente la mejor opción para ti. 🔋🚗

            En breve continuamos contigo.
            """,

            f"""
            Gracias {customer} 🙌

            Ya registramos correctamente la información de tu vehículo. Por ahora no encontré una coincidencia automática en el catálogo, pero nuestro equipo revisará la referencia adecuada para ayudarte. 🔋

            En unos momentos continuamos contigo.
            """,

            f"""
            Perfecto {customer} 🚗🔋

            Ya tenemos los datos de tu vehículo registrados. En este momento un asesor validará manualmente las baterías compatibles para brindarte la mejor recomendación posible.

            Gracias por comunicarte con Mega Baterías.
            """,
        ]

        return dedent(random.choice(messages)).strip()

    _store_last_catalog_options_on_session(session, options, "recommended")

    lines = [
        f"Perfecto {customer} 👍",
        "",
        "Según los datos de tu vehículo, encontré varias baterías compatibles.",
        "Para hacerlo más fácil, te comparto las opciones más recomendadas:",
        "",
    ]

    for index, option in enumerate(options, start=1):
        price = option.sale_price or option.min_sale_price or option.max_sale_price
        line_label = option._get_battery_line_label() if hasattr(option, "_get_battery_line_label") else option.battery_line

        option_lines = [
            f"Opción {index}:",
            f"• Línea: {line_label}",
            f"• Referencia: {option.reference}",
        ]

        if price:
            option_lines.append(f"• Precio sugerido: {format_money(price)}")

        if option.description:
            option_lines.append(f"• Descripción: {option.description}")

        lines.append("\n".join(option_lines))
        lines.append("")

    lines.append("")
    lines.append("Estos precios se sostienen dejando la batería usada")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("Para continuar, respóndeme con una de estas opciones:")
    lines.append("• Opción 1")
    lines.append("• Opción 2")
    lines.append("• Quiero hablar con un asesor")
    lines.append("")
    lines.append("Si decides continuar, un asesor confirmará disponibilidad y coordinará la entrega. 🔋🚗")

    return "\n".join(lines).strip()


def lead_has_battery_options(env, lead) -> bool:
    return bool(find_battery_options_for_lead(env, lead, limit=1))


def build_more_battery_options_message_for_lead(env, lead, session=None) -> str:
    all_options = find_battery_options_for_lead(env, lead, limit=20)
    recommended_options = get_recommended_battery_option_for_lead(env, lead)
    recommended_reference = recommended_options[0].reference if recommended_options else False

    customer = lead.contact_name or lead.partner_id.name or "señor/a"

    unique_options = []
    seen_references = set()

    for option in all_options:
        reference = (option.reference or "").strip()

        if not reference:
            continue

        if recommended_reference and reference == recommended_reference:
            continue

        if reference in seen_references:
            continue

        seen_references.add(reference)
        unique_options.append(option)

        if len(unique_options) == 3:
            break

    options = unique_options

    if not options:
        return (
            f"Claro {customer} 👍\n\n"
            "En este momento no encontré más opciones diferentes para tu vehículo. "
            "Podemos continuar con la opción recomendada o, si prefieres, un asesor de Mega Baterías puede revisarlo manualmente contigo. 🔋🚗"
        )

    _store_last_catalog_options_on_session(session, options, "more_options")

    lines = [
        f"Claro {customer} 👍",
        "",
        "Te comparto más opciones compatibles para tu vehículo:",
        "",
    ]

    for index, option in enumerate(options, start=1):
        price = option.sale_price or option.min_sale_price or option.max_sale_price
        line_label = option._get_battery_line_label() if hasattr(option, "_get_battery_line_label") else option.battery_line

        option_lines = [
            f"Opción {index}:",
            f"• Línea: {line_label}",
            f"• Referencia: {option.reference}",
        ]

        if price:
            option_lines.append(f"• Precio: {format_money(price)}")

        if option.description:
            option_lines.append(f"• Descripción: {option.description}")

        lines.append("\n".join(option_lines))
        lines.append("")

    lines.append("Los precios aplican entregando la batería usada.")
    lines.append("Si deseas quedarte con la batería usada, se adicionan $40.000.")
    lines.append("")
    lines.append("Para continuar, responde con la opción que prefieres o escribe “quiero asesor”.")

    return "\n".join(lines).strip()

def build_recommended_battery_message_for_lead(env, lead, session=None) -> str:
    options = get_recommended_battery_option_for_lead(env, lead)
    customer = lead.contact_name or lead.partner_id.name or "señor/a"

    if not options:
        return build_battery_catalog_message_for_lead(env, lead, session=session)

    option = options[0]
    _store_last_catalog_options_on_session(session, options, "recommended")

    price = get_battery_option_price(option)
    line_label = get_battery_line_label(option)

    lines = [
        f"Perfecto {customer} 👍",
        "",
        "Según los datos de tu vehículo, esta es la opción recomendada:",
        "",
        f"🔋 Línea: {line_label}",
        f"📌 Referencia: {option.reference}",
    ]

    if price:
        lines.append(f"💰 Precio: {format_money(price)}")

    lines.append("")
    lines.append("Este precio aplica entregando la batería usada.")
    lines.append("Si deseas quedarte con la batería usada, se adicionan $40.000.")
    lines.append("")
    return "\n".join(lines).strip()


def get_recommended_battery_option_for_lead(env, lead):
    """Return the same first option used by the recommended catalog message."""
    options = find_battery_options_for_lead(env, lead, limit=1)
    return options[:1]


def get_battery_option_for_catalog_index(env, lead, option_index: int = 1, session=None):
    """Return the option shown at option_index in the catalog message."""
    try:
        option_index = int(option_index or 1)
    except (TypeError, ValueError):
        option_index = 1

    option_index = max(1, min(option_index, 3))
    session_option = _get_session_catalog_options(env, session, option_index)
    if session_option is not None:
        return session_option

    options = find_battery_options_for_lead(env, lead, limit=3)
    return options[option_index - 1:option_index]
