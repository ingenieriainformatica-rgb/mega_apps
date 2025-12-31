import logging
from odoo.http import request  # type: ignore

_logger = logging.getLogger(__name__)


def get_sales_data(date_from=None, date_to=None):
    warehouses = get_active_warehouses()
    sales_by_wh, grand = get_sales_by_warehouse(
        warehouses=warehouses,
        date_from=date_from,
        date_to=date_to,
    )

    return {
        "ok": True,
        "date_from": date_from,
        "date_to": date_to,
        "warehouses": [
            {"id": wh.id, "name": wh.name}
            for wh in warehouses
        ],
        "sales_by_warehouse": sales_by_wh,
        "grand": grand,
    }


def get_active_warehouses():
    """Retorna almacenes (warehouses) activos de la compañía actual."""
    Warehouse = request.env["stock.warehouse"].sudo()
    company = request.env.company
    return Warehouse.search([("company_id", "=", company.id)], order="name")


def get_sales_by_warehouse(warehouses, date_from=None, date_to=None):
    """
    Ventas por almacén basadas en sale.order:
    - Solo órdenes confirmadas / finalizadas
    - Solo órdenes totalmente facturadas (invoice_status = 'invoiced')
    """
    SaleOrder = request.env["sale.order"].sudo()
    company = request.env.company

    domain_base = [
        ("company_id", "=", company.id),
        ("state", "in", ["sale", "done"]),
        ("invoice_status", "=", "invoiced"),  # SOLO facturadas
    ]

    # Fechas (usa date_order). Si prefieres por fecha de factura, me dices y lo cambiamos.
    if date_from:
        domain_base.append(("date_order", ">=", date_from))
    if date_to:
        domain_base.append(("date_order", "<=", date_to))

    sales_by_wh = []
    grand_total = 0.0
    grand_count = 0

    for wh in warehouses:
        domain = domain_base + [("warehouse_id", "=", wh.id)]
        orders = SaleOrder.search(domain)

        total = sum(orders.mapped("amount_total"))
        count = len(orders)

        sales_by_wh.append({
            "warehouse_id": wh.id,
            "warehouse_name": wh.name,
            "count_orders": count,
            "total_sales": float(total),
        })

        grand_total += total
        grand_count += count

    return sales_by_wh, {
        "count_orders": grand_count,
        "total_sales": float(grand_total),
    }
