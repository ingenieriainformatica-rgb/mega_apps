import logging
from collections import defaultdict
from odoo.http import request  # type: ignore

_logger = logging.getLogger(__name__)

def get_active_warehouses():
    Warehouse = request.env["stock.warehouse"].sudo()
    company = request.env.company
    return Warehouse.search([("company_id", "=", company.id)], order="name")

def get_sales_by_warehouse_from_invoices(warehouses, date_from=None, date_to=None):
    """
    Ventas por bodega BASADAS EN FACTURAS (account.move):
    - move_type = out_invoice (facturas cliente)
    - state = posted
    - fecha = invoice_date (o date contable si necesitas)
    Devuelve subtotal (untaxed) + total (taxed) y cantidad de facturas.
    """

    company = request.env.company
    Move = request.env["account.move"].sudo()

    domain = [
        ("company_id", "=", company.id),
        ("move_type", "=", "out_invoice"),
        ("state", "=", "posted"),
    ]

    # ✅ usa invoice_date para que cuadre con análisis de facturas
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

    # Index de warehouses para no buscar en bucle
    wh_map = {wh.id: wh for wh in warehouses}

    for inv in invoices:
        # Detectar bodega: desde líneas -> sale_line_ids -> order -> warehouse_id
        wh_id = False
        for line in inv.invoice_line_ids:
            if line.sale_line_ids:
                so = line.sale_line_ids[0].order_id
                if so and so.warehouse_id:
                    wh_id = so.warehouse_id.id
                    break

        # Si no se pudo detectar bodega, lo mandamos a "Sin bodega"
        key = wh_id or 0

        bucket[key]["count_invoices"] += 1
        bucket[key]["subtotal_untaxed"] += inv.amount_untaxed
        bucket[key]["total_sales"] += inv.amount_total

    sales_by_wh = []
    grand_subtotal = 0.0
    grand_total = 0.0
    grand_count = 0

    # Generar salida para bodegas existentes
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

    # Agregar bucket "Sin bodega" si existe
    if 0 in bucket:
        data = bucket[0]
        sales_by_wh.append({
            "warehouse_id": 0,
            "warehouse_name": "Sin bodega",
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


def get_sales_data(date_from=None, date_to=None):
    warehouses = get_active_warehouses()

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
