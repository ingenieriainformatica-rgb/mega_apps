import logging
from textwrap import dedent
import random

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
        limit=3,
    )

    options = applications.mapped("option_ids").filtered(
        lambda option: option.sale_price or option.min_sale_price or option.max_sale_price
    )

    if not options:
        options = applications.mapped("option_ids")

    return options.sorted(
        key=lambda option: (
            option.option_number or 99,
            option.sale_price or option.min_sale_price or 0,
        )
    )[:limit]


def format_money(value) -> str:
    value = float(value or 0)
    return "${:,.0f}".format(value).replace(",", ".")


def build_battery_catalog_message_for_lead(env, lead) -> str:
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

        if option.stock_qty:
            option_lines.append(f"• Existencias: {option.stock_qty:g}")

        if option.description:
            option_lines.append(f"• Descripción: {option.description}")

        lines.append("\n".join(option_lines))
        lines.append("")

    lines.append("")
    lines.append("Estos precios se sostienen dejando la batería usada")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines).strip()


def lead_has_battery_options(env, lead) -> bool:
    return bool(find_battery_options_for_lead(env, lead, limit=1))
