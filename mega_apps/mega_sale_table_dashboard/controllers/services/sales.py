import logging
from collections import defaultdict
from odoo.http import request  # type: ignore

_logger = logging.getLogger(__name__)

# Campo nuevo en diarios (m2m)
JOURNAL_WH_FIELD = "warehouse_ids"


def get_active_warehouses(warehouse_id=None):
    Warehouse = request.env["stock.warehouse"].sudo()
    company = request.env.company

    if warehouse_id:
        return Warehouse.browse(int(warehouse_id))

    return Warehouse.search([
        ("company_id", "=", company.id),
        ("name", "not ilike", "GRUPOMEGA"),
    ], order="name")


def _get_journals_for_warehouses(warehouses):
    Journal = request.env["account.journal"].sudo()
    company = request.env.company
    wh_ids = warehouses.ids

    domain = [
        ("company_id", "=", company.id),
        ("type", "=", "sale"),
        (JOURNAL_WH_FIELD, "in", wh_ids),
    ]
    return Journal.search(domain)


def _warehouse_id_from_journal(journal):
    """
    Como warehouse_ids es m2m, para cuadrar 1:1 con pivot asumimos 1 bodega por diario.
    Tomamos la primera. Si no hay, 0.
    """
    whs = getattr(journal, JOURNAL_WH_FIELD, False)
    if not whs:
        return 0
    wh = whs[:1]  # first record (recordset de 1)
    return wh.id if wh else 0


def get_sales_by_warehouse_from_invoices(warehouses, date_from=None, date_to=None):
    """
    Igual al pivot (account.move):
    - out_invoice
    - state NOT IN (draft, cancel)
    - invoice_date entre fechas
    - journal_id en diarios mapeados a bodegas
    - bodega derivada desde journal.warehouse_ids (primera)
    """

    company = request.env.company
    Move = request.env["account.move"].sudo()

    journals = _get_journals_for_warehouses(warehouses)
    journal_ids = journals.ids

    domain = [
        ("company_id", "=", company.id),
        ("move_type", "=", "out_invoice"),
        ("state", "not in", ("draft", "cancel")),
    ]

    if journal_ids:
        domain.append(("journal_id", "in", journal_ids))
    else:
        # Si no hay mapeo diario->bodega, no vas a poder cuadrar con el pivot por "Diario"
        _logger.warning("No journals mapped to warehouses via %s", JOURNAL_WH_FIELD)
        # Igual dejamos que consulte todo (si lo prefieres puedes retornar ceros)
        # return [], {"count_invoices": 0, "subtotal_untaxed": 0.0, "total_sales": 0.0}, {}, {}

    if date_from:
        domain.append(("invoice_date", ">=", date_from))
    if date_to:
        domain.append(("invoice_date", "<=", date_to))

    # ✅ Para KPI sumamos sobre TODO el set
    invoices = Move.search(domain)

    # --- buckets KPI ---
    bucket = defaultdict(lambda: {
        "count_invoices": 0,
        "subtotal_untaxed": 0.0,
        "total_sales": 0.0,
    })

    # --- detalle facturas por bodega (para UI) ---
    invoices_by_wh = defaultdict(list)

    # --- productos por bodega (opcional) ---
    products_by_wh = defaultdict(lambda: defaultdict(lambda: {
        "product_id": 0,
        "product_name": "",
        "qty": 0.0,
        "subtotal": 0.0,
        "total": 0.0,
    }))

    for inv in invoices:
        wh_id = _warehouse_id_from_journal(inv.journal_id)  # ✅ clave

        bucket[wh_id]["count_invoices"] += 1
        bucket[wh_id]["subtotal_untaxed"] += inv.amount_untaxed
        bucket[wh_id]["total_sales"] += inv.amount_total

        # guardar facturas (limit por bodega para no reventar UI)
        invoices_by_wh[wh_id].append({
            "id": inv.id,
            "number": inv.name,  # o inv.payment_reference si usas otro
            "concepto": inv.x_studio_concepto or "",
            "partner": inv.partner_id.name or "",
            "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
            "journal": inv.journal_id.name or "",
            "subtotal_untaxed": float(inv.amount_untaxed),
            "total": float(inv.amount_total),
        })

        # productos (opcional)
        for line in inv.invoice_line_ids:
            if not line.product_id:
                continue
            p = products_by_wh[wh_id][line.product_id.id]
            p["product_id"] = line.product_id.id
            p["product_name"] = line.product_id.display_name
            p["qty"] += float(line.quantity or 0.0)
            # price_subtotal: sin impuestos, price_total: con impuestos (depende config)
            p["subtotal"] += float(getattr(line, "price_subtotal", 0.0) or 0.0)
            p["total"] += float(getattr(line, "price_total", 0.0) or 0.0)

    # salida KPI por bodega (solo bodegas seleccionadas)
    sales_by_wh = []
    grand = {"count_invoices": 0, "subtotal_untaxed": 0.0, "total_sales": 0.0}

    for wh in warehouses:
        data = bucket.get(wh.id) or {"count_invoices": 0, "subtotal_untaxed": 0.0, "total_sales": 0.0}
        sales_by_wh.append({
            "warehouse_id": wh.id,
            "warehouse_name": wh.name,
            "count_invoices": int(data["count_invoices"]),
            "subtotal_untaxed": float(data["subtotal_untaxed"]),
            "total_sales": float(data["total_sales"]),
        })
        grand["count_invoices"] += int(data["count_invoices"])
        grand["subtotal_untaxed"] += float(data["subtotal_untaxed"])
        grand["total_sales"] += float(data["total_sales"])

    # normalizar products_by_wh a lista top
    products_out = {}
    for wh_id, prod_map in products_by_wh.items():
        arr = list(prod_map.values())
        # top por total
        arr.sort(key=lambda x: x["total"], reverse=True)
        products_out[wh_id] = arr[:20]

    return sales_by_wh, grand, invoices_by_wh, products_out


def get_sales_data(date_from=None, date_to=None, warehouse_id=None):
    warehouses = get_active_warehouses(warehouse_id)

    sales_by_wh, grand, invoices_by_wh, products_by_wh = get_sales_by_warehouse_from_invoices(
        warehouses=warehouses,
        date_from=date_from,
        date_to=date_to,
    )

    # ✅ 1) invoices_by_warehouse como ARRAY (lista de bodegas con sus facturas)
    invoices_by_warehouse_arr = []
    for wh in warehouses:
        invoices_by_warehouse_arr.append({
            "warehouse_id": wh.id,
            "warehouse_name": wh.name,
            "invoices": invoices_by_wh.get(wh.id, []),  # ✅ siempre list
        })

    # ✅ 2) invoices_list plano (ARRAY) para UI cuando se filtra por 1 bodega
    # Si no se filtra bodega, lo dejamos vacío (o puedes concatenar todas si quieres)
    invoices_list = []
    if warehouse_id:
        invoices_list = invoices_by_wh.get(int(warehouse_id), [])

    return {
        "ok": True,
        "date_from": date_from,
        "date_to": date_to,
        "warehouses": [{"id": wh.id, "name": wh.name} for wh in warehouses],
        "sales_by_warehouse": sales_by_wh,
        "grand": grand,

        # ✅ YA NORMALIZADO PARA FRONT (arrays)
        "invoices_by_warehouse": invoices_by_warehouse_arr,  # ✅ array
        "invoices_list": invoices_list,                      # ✅ array

        # productos (ya estaba OK; ojo: products_by_wh ya te lo devuelves como dict con wh_id)
        "products_by_warehouse": products_by_wh,
    }

