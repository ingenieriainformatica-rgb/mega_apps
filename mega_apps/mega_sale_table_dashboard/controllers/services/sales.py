import logging
from collections import defaultdict
from odoo.http import request  # type: ignore
from .utils import get_active_warehouses  # type: ignore

_logger = logging.getLogger(__name__)

JOURNAL_WH_FIELD = "warehouse_ids"
ALL_HEADQUARTERS = "allHeadquarters"
ALL_JOURNAL = "allJournal"


def _norm_id(value, all_token):
    """Devuelve None si es vacío o token ALL, si no int()."""
    if value in ("", None, False, all_token):
        return None
    return int(value)


def _get_journals_for_warehouses(warehouses, journal_id=None):
    """Trae diarios de venta mapeados a las bodegas dadas (y opcional filtra 1 diario)."""
    Journal = request.env["account.journal"].sudo()
    company = request.env.company

    domain = [
        ("company_id", "=", company.id),
        ("type", "=", "sale"),
        (JOURNAL_WH_FIELD, "in", warehouses.ids),
    ]
    if journal_id:
        domain.append(("id", "=", int(journal_id)))

    return Journal.search(domain, order="name")


def _get_kpis_grouped(warehouses, journals, date_from=None, date_to=None, move_type=None, negate=False):
    """
    KPIs agrupados por (warehouse_id, journal_id).
    move_type: 'out_invoice' o 'out_refund'
    negate=True => valores en negativo
    """
    Move = request.env["account.move"].sudo()
    company = request.env.company

    if not journals:
        return {}, {}

    domain = [
        ("company_id", "=", company.id),
        ("state", "not in", ("draft", "cancel")),
        ("journal_id", "in", journals.ids),
    ]
    if move_type:
        domain.append(("move_type", "=", move_type))
    if date_from:
        domain.append(("invoice_date", ">=", date_from))
    if date_to:
        domain.append(("invoice_date", "<=", date_to))

    moves = Move.search(domain)
    sign = -1.0 if negate else 1.0

    kpi = defaultdict(lambda: {"count_invoices": 0, "subtotal_untaxed": 0.0, "total_sales": 0.0})
    detail = defaultdict(list)

    j_wh_map = {j.id: getattr(j, JOURNAL_WH_FIELD).ids for j in journals}

    for mv in moves:
        wh_ids = j_wh_map.get(mv.journal_id.id) or []
        if not wh_ids:
            continue

        wh_id = wh_ids[0]  # regla 1:1 (tomas la primera)
        key = (wh_id, mv.journal_id.id)

        kpi[key]["count_invoices"] += 1
        kpi[key]["subtotal_untaxed"] += float(mv.amount_untaxed) * sign
        kpi[key]["total_sales"] += float(mv.amount_total) * sign

        detail[key].append({
            "id": mv.id,
            "number": mv.name,
            "partner": mv.partner_id.name or "",
            "invoice_date": mv.invoice_date.isoformat() if mv.invoice_date else None,
            "journal_id": mv.journal_id.id,
            "journal": mv.journal_id.name or "",
            "move_type": mv.move_type,
            "concepto": getattr(mv, "x_studio_concepto", "") or "",
            "subtotal_untaxed": float(mv.amount_untaxed) * sign,
            "total": float(mv.amount_total) * sign,
        })

    return kpi, detail


def _get_concept_totals_grouped(journals, date_from=None, date_to=None, move_type=None, negate=False):
    """
    Totales agrupados por (warehouse_id, journal_id, concepto).
    Devuelve dict: (wh_id, journal_id) -> { concepto -> {count, subtotal_untaxed, total_sales} }
    """
    Move = request.env["account.move"].sudo()

    if not journals:
        return {}

    domain = [
        ("company_id", "=", request.env.company.id),
        ("state", "not in", ("draft", "cancel")),
        ("journal_id", "in", journals.ids),
    ]
    if move_type:
        domain.append(("move_type", "=", move_type))
    if date_from:
        domain.append(("invoice_date", ">=", date_from))
    if date_to:
        domain.append(("invoice_date", "<=", date_to))

    sign = -1.0 if negate else 1.0

    rows = Move.read_group(
        domain=domain,
        fields=["amount_untaxed:sum", "amount_total:sum", "id:count", "journal_id", "x_studio_concepto"],
        groupby=["journal_id", "x_studio_concepto"],
        lazy=False,
    )

    # journal_id -> wh_id (primera bodega)
    j_wh_map = {j.id: (getattr(j, JOURNAL_WH_FIELD).ids or [None])[0] for j in journals}

    out = defaultdict(lambda: defaultdict(lambda: {"count": 0, "subtotal_untaxed": 0.0, "total_sales": 0.0}))

    for r in rows:
        j_id = r["journal_id"][0] if r.get("journal_id") else None
        if not j_id:
            continue

        wh_id = j_wh_map.get(j_id)
        if not wh_id:
            continue

        concepto = (r.get("x_studio_concepto") or "").strip() or "SIN CONCEPTO"
        key = (wh_id, j_id)

        cnt = int(r.get("__count", 0) or r.get("id_count", 0) or 0)
        untaxed = float(r.get("amount_untaxed", 0.0) or r.get("amount_untaxed_sum", 0.0) or 0.0)
        total = float(r.get("amount_total", 0.0) or r.get("amount_total_sum", 0.0) or 0.0)

        out[key][concepto]["count"] += cnt
        out[key][concepto]["subtotal_untaxed"] += untaxed * sign
        out[key][concepto]["total_sales"] += total * sign

    return out


def get_sales_data(date_from=None, date_to=None, warehouse_id=None, journal_id=None):
    # 1) Normalizar tokens ALL
    wh_id = _norm_id(warehouse_id, ALL_HEADQUARTERS)   # None => todas sedes
    j_id = _norm_id(journal_id, ALL_JOURNAL)           # None => todos diarios

    # 2) Traer bodegas activas
    warehouses = get_active_warehouses(wh_id)

    # 3) Diarios por bodegas
    journals = _get_journals_for_warehouses(warehouses, journal_id=j_id)

    # 4) KPIs por (warehouse, journal)
    inv_kpi, inv_detail = _get_kpis_grouped(warehouses, journals, date_from, date_to, "out_invoice", negate=False)
    ref_kpi, ref_detail = _get_kpis_grouped(warehouses, journals, date_from, date_to, "out_refund", negate=True)

    # ✅ 5) Totales por concepto (FACTURAS y NC)
    inv_concept = _get_concept_totals_grouped(journals, date_from, date_to, "out_invoice", negate=False)
    ref_concept = _get_concept_totals_grouped(journals, date_from, date_to, "out_refund", negate=True)

    # 6) Armar respuesta por sede -> diarios
    groups = []
    grand = {"count_invoices": 0, "subtotal_untaxed": 0.0, "total_sales": 0.0}
    grand_refunds = {"count_invoices": 0, "subtotal_untaxed": 0.0, "total_sales": 0.0}

    for wh in warehouses:
        wh_journals = [j for j in journals if wh.id in getattr(j, JOURNAL_WH_FIELD).ids]
        wh_block = {"warehouse": {"id": wh.id, "name": wh.name}, "journals": []}

        for j in wh_journals:
            key = (wh.id, j.id)

            f = inv_kpi.get(key, {"count_invoices": 0, "subtotal_untaxed": 0.0, "total_sales": 0.0})
            r = ref_kpi.get(key, {"count_invoices": 0, "subtotal_untaxed": 0.0, "total_sales": 0.0})

            # sumar grands
            grand["count_invoices"] += int(f["count_invoices"])
            grand["subtotal_untaxed"] += float(f["subtotal_untaxed"])
            grand["total_sales"] += float(f["total_sales"])

            grand_refunds["count_invoices"] += int(r["count_invoices"])
            grand_refunds["subtotal_untaxed"] += float(r["subtotal_untaxed"])
            grand_refunds["total_sales"] += float(r["total_sales"])

            # detalle
            moves = (inv_detail.get(key, []) + ref_detail.get(key, []))
            moves.sort(key=lambda x: x["invoice_date"] or "", reverse=True)

            has_invoices = int(f["count_invoices"]) > 0
            has_credit_notes = int(r["count_invoices"]) > 0

            # ✅ merge de conceptos (facturas + NC)
            conceptos = {}

            for name, v in inv_concept.get(key, {}).items():
                conceptos[name] = {
                    "count": int(v["count"]),
                    "subtotal_untaxed": float(v["subtotal_untaxed"]),
                    "total_sales": float(v["total_sales"]),
                }

            for name, v in ref_concept.get(key, {}).items():
                if name not in conceptos:
                    conceptos[name] = {"count": 0, "subtotal_untaxed": 0.0, "total_sales": 0.0}
                conceptos[name]["count"] += int(v["count"])
                conceptos[name]["subtotal_untaxed"] += float(v["subtotal_untaxed"])
                conceptos[name]["total_sales"] += float(v["total_sales"])

            conceptos_list = [{"concepto": k, **val} for k, val in conceptos.items()]
            conceptos_list.sort(key=lambda x: x["total_sales"], reverse=True)

            wh_block["journals"].append({
                "journal": {"id": j.id, "name": j.name},
                "is_credit_note_journal": has_credit_notes and not has_invoices,

                "facturado": {
                    "count_invoices": int(f["count_invoices"]),
                    "subtotal_untaxed": float(f["subtotal_untaxed"]),
                    "total_sales": float(f["total_sales"]),
                },
                "notas_credito": {
                    "count_invoices": int(r["count_invoices"]),
                    "subtotal_untaxed": float(r["subtotal_untaxed"]),
                    "total_sales": float(r["total_sales"]),
                },

                # ✅ NUEVO: totales por concepto (asesor)
                "conceptos_totales": conceptos_list,

                "moves": moves,
            })

        if wh_block["journals"]:
            groups.append(wh_block)

    selected_journal = None
    if j_id:
        j = request.env["account.journal"].sudo().browse(j_id)
        if j.exists():
            selected_journal = {"id": j.id, "name": j.name}

    return {
        "ok": True,
        "date_from": date_from,
        "date_to": date_to,
        "selected_journal": selected_journal,
        "warehouses": [{"id": w.id, "name": w.name} for w in warehouses],
        "journals": [{"id": j.id, "name": j.name} for j in journals],
        "grand": grand,
        "grand_refunds": grand_refunds,
        "groups": groups,
    }
