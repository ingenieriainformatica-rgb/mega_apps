import logging
from collections import defaultdict
from odoo.http import request  # type: ignore

_logger = logging.getLogger(__name__)


# ✅ Ajusta este nombre si tu campo se llama diferente
JOURNAL_WH_FIELD = "warehouse_ids"


def get_active_warehouses(warehouse_id=None):
    Warehouse = request.env["stock.warehouse"].sudo()
    company = request.env.company
    if warehouse_id:
        warehouses = Warehouse.browse(int(warehouse_id))
    else:
        warehouses = Warehouse.search([("company_id", "=", company.id)], order="name")
    return warehouses


def _get_journals_for_warehouses(warehouses):
    """
    Devuelve diarios de venta asociados a esas bodegas, usando el campo nuevo del diario.
    """
    Journal = request.env["account.journal"].sudo()
    company = request.env.company

    wh_ids = warehouses.ids
    domain = [
        ("company_id", "=", company.id),
        ("type", "=", "sale"),
        (JOURNAL_WH_FIELD, "in", wh_ids),
    ]
    return Journal.search(domain)


def get_sales_by_warehouse_from_invoices(warehouses, date_from=None, date_to=None):
    """
    Ventas por bodega BASADAS EN FACTURAS (account.move) igual al pivot:
    - Facturas cliente (out_invoice)
    - Estado NOT IN (draft, cancel)
    - Fecha: invoice_date (igual a "Fecha" del análisis de facturas)
    - Diario(s): los diarios que pertenezcan a las bodegas seleccionadas
    - Bodega: se toma desde el diario -> journal.x_warehouse_id (NO desde sale_line_ids)
    """

    _logger.info(
        "\n\n get_sales_by_warehouse_from_invoices date_from=%s date_to=%s wh_ids=%s \n\n",
        date_from, date_to, warehouses.ids
    )

    company = request.env.company
    Move = request.env["account.move"].sudo()

    # ✅ diarios asociados a las bodegas seleccionadas
    journals = _get_journals_for_warehouses(warehouses)
    journal_ids = journals.ids

    _logger.info(f"\n\n  Esto -> {journal_ids} -> {warehouses} \n\n")

    domain = [
        ("company_id", "=", company.id),
        ("move_type", "=", "out_invoice"),
        ("state", "not in", ("draft", "cancel")),
    ]

    # ✅ si hay diarios configurados por bodega, filtra por ellos (esto te cuadra con pivot)
    if journal_ids:
        domain.append(("journal_id", "in", journal_ids))
    else:
        # Si no hay diarios mapeados, mejor no filtrar por diario para no “matar” datos
        _logger.warning("No journals mapped to warehouses via %s. Returning zeros.", JOURNAL_WH_FIELD)

    # ✅ usa invoice_date (pivot usa “Fecha” de factura normalmente)
    if date_from:
        domain.append(("invoice_date", ">=", date_from))
    if date_to:
        domain.append(("invoice_date", "<=", date_to))

    invoices = Move.search(domain)

    # Acumuladores por bodega
    bucket = defaultdict(lambda: {
        "count_invoices": 0,
        "subtotal_untaxed": 0.0,
        "total_sales": 0.0,
    })

    for inv in invoices:
        # ✅ Bodega desde el diario (esto es lo que hace que cuadre 1:1 con pivot por diario)
        wh = getattr(inv.journal_id, JOURNAL_WH_FIELD, False)
        wh_id = wh.id if wh else 0

        bucket[wh_id]["count_invoices"] += 1
        bucket[wh_id]["subtotal_untaxed"] += inv.amount_untaxed
        bucket[wh_id]["total_sales"] += inv.amount_total

    sales_by_wh = []
    grand_subtotal = 0.0
    grand_total = 0.0
    grand_count = 0

    for wh in warehouses:
        data = bucket.get(wh.id) or {"count_invoices": 0, "subtotal_untaxed": 0.0, "total_sales": 0.0}
        sales_by_wh.append({
            "warehouse_id": wh.id,
            "warehouse_name": wh.name,
            "count_invoices": data["count_invoices"],
            "subtotal_untaxed": float(data["subtotal_untaxed"]),
            "total_sales": float(data["total_sales"]),
        })
        grand_count += data["count_invoices"]
        grand_subtotal += data["subtotal_untaxed"]
        grand_total += data["total_sales"]

    return sales_by_wh, {
        "count_invoices": grand_count,
        "subtotal_untaxed": float(grand_subtotal),
        "total_sales": float(grand_total),
    }


def get_sales_data(date_from=None, date_to=None, warehouse_id=None):
    warehouses = get_active_warehouses(warehouse_id)

    sales_by_wh, grand = get_sales_by_warehouse_from_invoices(
        warehouses=warehouses,
        date_from=date_from,
        date_to=date_to,
    )

    return {
        "ok": True,
        "date_from": date_from,
        "date_to": date_to,
        "warehouses": [{"id": wh.id, "name": wh.name} for wh in warehouses],
        "sales_by_warehouse": sales_by_wh,
        "grand": grand,
    }
