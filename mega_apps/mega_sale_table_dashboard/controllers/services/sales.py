import logging
from collections import defaultdict
from odoo.http import request  # type: ignore
from .utils import (  #type: ignore
    get_active_warehouses
)

_logger = logging.getLogger(__name__)

# Campo nuevo en diarios (m2m)
JOURNAL_WH_FIELD = "warehouse_ids"


def _get_journals_for_warehouses(warehouses, journal_id=None):
    Journal = request.env["account.journal"].sudo()
    company = request.env.company
    wh_ids = warehouses.ids

    domain = [
        ("company_id", "=", company.id),
        ("type", "=", "sale"),
        (JOURNAL_WH_FIELD, "in", wh_ids),
    ]

    if journal_id:
        domain.append(("id", "=", int(journal_id)))

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

def _get_kpis_by_warehouse(
    warehouses,
    date_from=None,
    date_to=None,
    journal_id=None,
    negate=False,
):
    company = request.env.company
    Move = request.env["account.move"].sudo()

    journals = _get_journals_for_warehouses(warehouses, journal_id=journal_id)
    journal_ids = journals.ids

    domain = [
        ("company_id", "=", company.id),
        ("state", "not in", ("draft", "cancel")),
    ]

    # Si hay journals mapeados, filtramos por ellos
    if journal_ids:
        domain.append(("journal_id", "in", journal_ids))
    else:
        # Si NO hay mapeo, no tiene sentido para tu dashboard
        return [], {"count": 0, "untaxed": 0.0, "total": 0.0}, defaultdict(list)

    if date_from:
        domain.append(("invoice_date", ">=", date_from))
    if date_to:
        domain.append(("invoice_date", "<=", date_to))

    moves = Move.search(domain)

    sign = -1.0 if negate else 1.0  # ✅ NC en negativo

    bucket = defaultdict(lambda: {"count": 0, "untaxed": 0.0, "total": 0.0})
    moves_by_wh = defaultdict(list)

    for mv in moves:
        wh_id = _warehouse_id_from_journal(mv.journal_id)

        bucket[wh_id]["count"] += 1
        bucket[wh_id]["untaxed"] += (mv.amount_untaxed * sign)
        bucket[wh_id]["total"] += (mv.amount_total * sign)

        moves_by_wh[wh_id].append({
            "id": mv.id,
            "number": mv.name,
            "partner": mv.partner_id.name or "",
            "invoice_date": mv.invoice_date.isoformat() if mv.invoice_date else None,
            "journal_id": mv.journal_id.id,
            "journal": mv.journal_id.name or "",
            "concepto": getattr(mv, "x_studio_concepto", "") or "",
            "move_type": mv.move_type,  # ✅ útil en front
            "subtotal_untaxed": float(mv.amount_untaxed * sign),
            "total": float(mv.amount_total * sign),
        })

    out = []
    grand = {"count": 0, "untaxed": 0.0, "total": 0.0}

    for wh in warehouses:
        data = bucket.get(wh.id) or {"count": 0, "untaxed": 0.0, "total": 0.0}
        out.append({
            "warehouse_id": wh.id,
            "warehouse_name": wh.name,
            "count_invoices": int(data["count"]),
            "subtotal_untaxed": float(data["untaxed"]),
            "total_sales": float(data["total"]),
        })
        grand["count"] += int(data["count"])
        grand["untaxed"] += float(data["untaxed"])
        grand["total"] += float(data["total"])

    return out, {
        "count_invoices": int(grand["count"]),
        "subtotal_untaxed": float(grand["untaxed"]),
        "total_sales": float(grand["total"]),
    }, moves_by_wh


def get_sales_data(date_from=None, date_to=None, warehouse_id=None, journal_id=None):
    warehouses = get_active_warehouses(warehouse_id)
    # 1) JOURNAL SELECCIONADO (para pintar nombre arriba)
    selected_journal = None
    if journal_id and journal_id not in ("allJournal", "", None):
        j = request.env["account.journal"].sudo().browse(int(journal_id))
        if j.exists():
            selected_journal = {"id": j.id, "name": j.name}

    # Normalizar journal_id
    real_journal_id = None
    if journal_id and journal_id not in ("allJournal", "", None):
        real_journal_id = int(journal_id)

    _logger.info(f"\n\n Infordata otro -> {date_from} -> {date_to} -> {warehouse_id} -> {journal_id} -> {real_journal_id} \n\n")

    # 2) FACTURAS (out_invoice)
    sales_by_wh, grand, invoices_by_wh = _get_kpis_by_warehouse(
        warehouses=warehouses,
        date_from=date_from,
        date_to=date_to,
        journal_id=real_journal_id,
        negate=False,
    )

    # 3) NOTAS CRÉDITO (out_refund)  ✅ esto es lo correcto en Odoo
    refunds_by_wh, grand_refunds, refunds_by_wh_detail = _get_kpis_by_warehouse(
        warehouses=warehouses,
        date_from=date_from,
        date_to=date_to,
        journal_id=real_journal_id,
        negate=True,
    )

    # 4) invoices_list (solo cuando filtras por una sede)
    invoices_list = []
    if warehouse_id and warehouse_id not in ("allHeadquarters", "", None):
        invoices_list = invoices_by_wh.get(int(warehouse_id), [])

    # 5) refunds_list (solo cuando filtras por una sede)
    refunds_list = []
    if warehouse_id and warehouse_id not in ("allHeadquarters", "", None):
        refunds_list = refunds_by_wh_detail.get(int(warehouse_id), [])

    return {
        "ok": True,
        "date_from": date_from,
        "date_to": date_to,

        "selected_journal": selected_journal,

        "warehouses": [{"id": wh.id, "name": wh.name} for wh in warehouses],

        # FACTURADO
        "sales_by_warehouse": sales_by_wh,
        "grand": grand,
        "invoices_by_warehouse": [
            {"warehouse_id": wh.id, "warehouse_name": wh.name, "invoices": invoices_by_wh.get(wh.id, [])}
            for wh in warehouses
        ],
        "invoices_list": invoices_list,

        # NOTAS CRÉDITO
        "refunds_by_warehouse": refunds_by_wh,
        "grand_refunds": grand_refunds,
        "refunds_list": refunds_list,
    }
