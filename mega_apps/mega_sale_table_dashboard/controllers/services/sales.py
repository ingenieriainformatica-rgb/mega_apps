import logging
from collections import defaultdict
from datetime import date as date_cls, timedelta
from odoo.http import request  # type: ignore
from . import analytics  # type: ignore
from .utils import get_active_warehouses, get_allowed_company_ids, state_domain as _state_domain  # type: ignore

_logger = logging.getLogger(__name__)

JOURNAL_WH_FIELD = "warehouse_ids"
ALL_HEADQUARTERS = "allHeadquarters"
ALL_JOURNAL = "allJournal"
ALL_TEAMS = "allTeams"


# ─────────────────────────────────────────────────────────────────
# Helpers de normalización
# ─────────────────────────────────────────────────────────────────

def _norm_id(value, all_token):
    """Devuelve None si es vacío o token ALL, si no int()."""
    if value in ("", None, False, all_token):
        return None
    return int(value)


def _get_previous_period_dates(date_from, date_to):
    """
    Calcula el período anterior de la misma duración, inmediatamente antes.
    Ejemplo: jul 1–31 (31 días) → jun 1–30 (31 días previos).
    """
    if not date_from or not date_to:
        return None, None
    try:
        d_from = date_cls.fromisoformat(str(date_from))
        d_to = date_cls.fromisoformat(str(date_to))
        delta = (d_to - d_from).days + 1          # duración del período actual
        prev_date_to = d_from - timedelta(days=1)  # día anterior al inicio actual
        prev_date_from = prev_date_to - timedelta(days=delta - 1)
        return str(prev_date_from), str(prev_date_to)
    except (ValueError, TypeError):
        return None, None


# ─────────────────────────────────────────────────────────────────
# Consultas de diarios
# ─────────────────────────────────────────────────────────────────

def _get_journals_for_warehouses(warehouses, journal_id=None, company_ids=None):
    """Trae diarios de venta mapeados a las bodegas dadas (y opcional filtra 1 diario)."""
    Journal = request.env["account.journal"].sudo()

    domain = [
        ("company_id", "in", company_ids or get_allowed_company_ids()),
        ("type", "=", "sale"),
        (JOURNAL_WH_FIELD, "in", warehouses.ids),
    ]
    if journal_id:
        domain.append(("id", "=", int(journal_id)))

    return Journal.search(domain, order="name")


# ─────────────────────────────────────────────────────────────────
# KPIs agrupados — versión detallada (período actual, con moves)
# ─────────────────────────────────────────────────────────────────

def _get_kpis_grouped(warehouses, journals, date_from=None, date_to=None, move_type=None, negate=False, advisor_name=None, team_id=None, state_filter=None, company_ids=None):
    """
    KPIs agrupados por (warehouse_id, journal_id).
    move_type: 'out_invoice' o 'out_refund'
    negate=True => valores en negativo
    advisor_name: si se da, filtra por x_studio_concepto (comparación sin
                  distinguir mayúsculas/minúsculas)
    """
    Move = request.env["account.move"].sudo()

    if not journals:
        return {}, {}

    domain = [
        ("company_id", "in", company_ids or get_allowed_company_ids()),
        ("journal_id", "in", journals.ids),
    ] + _state_domain(state_filter)
    if move_type:
        domain.append(("move_type", "=", move_type))
    if date_from:
        domain.append(("invoice_date", ">=", date_from))
    if date_to:
        domain.append(("invoice_date", "<=", date_to))
    if advisor_name:
        domain.append(("x_studio_concepto", "=ilike", advisor_name))
    if team_id:
        domain.append(("team_id", "=", int(team_id)))

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


# ─────────────────────────────────────────────────────────────────
# Totales por concepto (asesor)
# ─────────────────────────────────────────────────────────────────

def _get_concept_totals_grouped(journals, date_from=None, date_to=None, move_type=None, negate=False, advisor_name=None, team_id=None, state_filter=None, company_ids=None):
    """
    Totales agrupados por (warehouse_id, journal_id, concepto).
    Devuelve dict: (wh_id, journal_id) -> { concepto -> {count, subtotal_untaxed, total_sales} }
    """
    Move = request.env["account.move"].sudo()

    if not journals:
        return {}

    domain = [
        ("company_id", "in", company_ids or get_allowed_company_ids()),
        ("journal_id", "in", journals.ids),
    ] + _state_domain(state_filter)
    if move_type:
        domain.append(("move_type", "=", move_type))
    if date_from:
        domain.append(("invoice_date", ">=", date_from))
    if date_to:
        domain.append(("invoice_date", "<=", date_to))
    if advisor_name:
        domain.append(("x_studio_concepto", "=ilike", advisor_name))
    if team_id:
        domain.append(("team_id", "=", int(team_id)))

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


# ─────────────────────────────────────────────────────────────────
# Totales por cliente (empresa/contacto de la factura)
# ─────────────────────────────────────────────────────────────────

def _get_partner_totals_grouped(journals, date_from=None, date_to=None, move_type=None, negate=False, advisor_name=None, team_id=None, state_filter=None, company_ids=None):
    """
    Totales agrupados por (warehouse_id, journal_id, cliente).
    Devuelve dict: (wh_id, journal_id) -> { partner_id -> {count, subtotal_untaxed, total_sales, partner_name, vat} }
    """
    Move = request.env["account.move"].sudo()

    if not journals:
        return {}

    domain = [
        ("company_id", "in", company_ids or get_allowed_company_ids()),
        ("journal_id", "in", journals.ids),
    ] + _state_domain(state_filter)
    if move_type:
        domain.append(("move_type", "=", move_type))
    if date_from:
        domain.append(("invoice_date", ">=", date_from))
    if date_to:
        domain.append(("invoice_date", "<=", date_to))
    if advisor_name:
        domain.append(("x_studio_concepto", "=ilike", advisor_name))
    if team_id:
        domain.append(("team_id", "=", int(team_id)))

    sign = -1.0 if negate else 1.0

    rows = Move.read_group(
        domain=domain,
        fields=["amount_untaxed:sum", "amount_total:sum", "id:count", "journal_id", "partner_id"],
        groupby=["journal_id", "partner_id"],
        lazy=False,
    )

    # journal_id -> wh_id (primera bodega)
    j_wh_map = {j.id: (getattr(j, JOURNAL_WH_FIELD).ids or [None])[0] for j in journals}

    # NIT de cada cliente en un solo query (evita N+1)
    partner_ids = [r["partner_id"][0] for r in rows if r.get("partner_id")]
    partners = request.env["res.partner"].sudo().browse(partner_ids)
    vat_map = {p.id: (p.vat or "") for p in partners}

    out = defaultdict(lambda: defaultdict(lambda: {
        "count": 0, "subtotal_untaxed": 0.0, "total_sales": 0.0,
        "partner_name": "", "vat": "",
    }))

    for r in rows:
        j_id = r["journal_id"][0] if r.get("journal_id") else None
        if not j_id:
            continue

        wh_id = j_wh_map.get(j_id)
        if not wh_id:
            continue

        if r.get("partner_id"):
            p_id, p_name = r["partner_id"]
        else:
            p_id, p_name = 0, "SIN CLIENTE"

        key = (wh_id, j_id)

        cnt = int(r.get("__count", 0) or r.get("id_count", 0) or 0)
        untaxed = float(r.get("amount_untaxed", 0.0) or r.get("amount_untaxed_sum", 0.0) or 0.0)
        total = float(r.get("amount_total", 0.0) or r.get("amount_total_sum", 0.0) or 0.0)

        bucket = out[key][p_id]
        bucket["partner_name"] = p_name
        bucket["vat"] = vat_map.get(p_id, "")
        bucket["count"] += cnt
        bucket["subtotal_untaxed"] += untaxed * sign
        bucket["total_sales"] += total * sign

    return out


# ─────────────────────────────────────────────────────────────────
# Totales globales rápidos — read_group sin cargar recordsets
# Usados para calcular el período anterior de forma eficiente.
# ─────────────────────────────────────────────────────────────────

def _get_grand_totals_fast(journals, date_from=None, date_to=None, move_type=None, negate=False, advisor_name=None, team_id=None, state_filter=None, company_ids=None):
    """
    Retorna totales globales usando read_group agrupado por journal_id.
    Eficiente: no carga registros individuales en memoria Python.
    """
    Move = request.env["account.move"].sudo()

    if not journals:
        return {"count_invoices": 0, "subtotal_untaxed": 0.0, "total_sales": 0.0}

    domain = [
        ("company_id", "in", company_ids or get_allowed_company_ids()),
        ("journal_id", "in", journals.ids),
    ] + _state_domain(state_filter)
    if move_type:
        domain.append(("move_type", "=", move_type))
    if date_from:
        domain.append(("invoice_date", ">=", date_from))
    if date_to:
        domain.append(("invoice_date", "<=", date_to))
    if advisor_name:
        domain.append(("x_studio_concepto", "=ilike", advisor_name))
    if team_id:
        domain.append(("team_id", "=", int(team_id)))

    rows = Move.read_group(
        domain=domain,
        fields=["amount_untaxed:sum", "amount_total:sum"],
        groupby=["journal_id"],
        lazy=False,
    )

    sign = -1.0 if negate else 1.0
    cnt = sum(int(r.get("__count", 0) or 0) for r in rows)
    untaxed = sum(float(r.get("amount_untaxed", 0.0) or 0.0) for r in rows) * sign
    total = sum(float(r.get("amount_total", 0.0) or 0.0) for r in rows) * sign

    return {"count_invoices": cnt, "subtotal_untaxed": untaxed, "total_sales": total}


# ─────────────────────────────────────────────────────────────────
# Función principal pública
# ─────────────────────────────────────────────────────────────────

def _resolve_advisor_name(advisor_id):
    """advisor_id (id de res.partner marcado is_advisor) -> nombre del contacto,
    o None si no se seleccionó ninguno (token vacío / "allAdvisors")."""
    if advisor_id in ("", None, False, "allAdvisors"):
        return None
    try:
        partner = request.env["res.partner"].sudo().browse(int(advisor_id))
    except (TypeError, ValueError):
        return None
    return partner.name if partner.exists() else None


def get_sales_data(date_from=None, date_to=None, warehouse_id=None, journal_id=None, advisor_id=None, team_id=None, state_filter=None, company_id=None):
    # 1) Normalizar tokens ALL
    wh_id = _norm_id(warehouse_id, ALL_HEADQUARTERS)   # None => todas sedes
    j_id = _norm_id(journal_id, ALL_JOURNAL)           # None => todos diarios
    advisor_name = _resolve_advisor_name(advisor_id)   # None => todos los asesores
    t_id = _norm_id(team_id, ALL_TEAMS)                # None => todos los equipos
    company_ids = get_allowed_company_ids(company_id)  # respeta allowed_company_ids

    # 2) Bodegas activas (de las compañías permitidas / seleccionada)
    warehouses = get_active_warehouses(wh_id, company_id=company_id)

    # 3) Diarios por bodegas
    journals = _get_journals_for_warehouses(warehouses, journal_id=j_id, company_ids=company_ids)

    _kw = dict(team_id=t_id, state_filter=state_filter, company_ids=company_ids)

    # 4) KPIs detallados por (warehouse, journal) — período actual
    inv_kpi, inv_detail = _get_kpis_grouped(warehouses, journals, date_from, date_to, "out_invoice", negate=False, advisor_name=advisor_name, **_kw)
    ref_kpi, ref_detail = _get_kpis_grouped(warehouses, journals, date_from, date_to, "out_refund", negate=True, advisor_name=advisor_name, **_kw)

    # 5) Totales por concepto (facturas + NC)
    inv_concept = _get_concept_totals_grouped(journals, date_from, date_to, "out_invoice", negate=False, advisor_name=advisor_name, **_kw)
    ref_concept = _get_concept_totals_grouped(journals, date_from, date_to, "out_refund", negate=True, advisor_name=advisor_name, **_kw)

    # 5b) Totales por cliente (facturas + NC)
    inv_partner = _get_partner_totals_grouped(journals, date_from, date_to, "out_invoice", negate=False, advisor_name=advisor_name, **_kw)
    ref_partner = _get_partner_totals_grouped(journals, date_from, date_to, "out_refund", negate=True, advisor_name=advisor_name, **_kw)

    # 6) Armar respuesta por sede → diarios
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

            grand["count_invoices"] += int(f["count_invoices"])
            grand["subtotal_untaxed"] += float(f["subtotal_untaxed"])
            grand["total_sales"] += float(f["total_sales"])

            grand_refunds["count_invoices"] += int(r["count_invoices"])
            grand_refunds["subtotal_untaxed"] += float(r["subtotal_untaxed"])
            grand_refunds["total_sales"] += float(r["total_sales"])

            moves = inv_detail.get(key, []) + ref_detail.get(key, [])
            moves.sort(key=lambda x: x["invoice_date"] or "", reverse=True)

            has_invoices = int(f["count_invoices"]) > 0
            has_credit_notes = int(r["count_invoices"]) > 0

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

            clientes = {}
            for p_id, v in inv_partner.get(key, {}).items():
                clientes[p_id] = {
                    "partner_name": v["partner_name"],
                    "vat": v["vat"],
                    "count": int(v["count"]),
                    "subtotal_untaxed": float(v["subtotal_untaxed"]),
                    "total_sales": float(v["total_sales"]),
                }
            for p_id, v in ref_partner.get(key, {}).items():
                if p_id not in clientes:
                    clientes[p_id] = {
                        "partner_name": v["partner_name"], "vat": v["vat"],
                        "count": 0, "subtotal_untaxed": 0.0, "total_sales": 0.0,
                    }
                clientes[p_id]["count"] += int(v["count"])
                clientes[p_id]["subtotal_untaxed"] += float(v["subtotal_untaxed"])
                clientes[p_id]["total_sales"] += float(v["total_sales"])

            clientes_list = [val for val in clientes.values()]
            clientes_list.sort(key=lambda x: x["total_sales"], reverse=True)

            # Solo se muestra el diario si tiene facturas o notas crédito en
            # el período/filtro actual - evita tarjetas vacías ($0 - 0 facturas).
            if not (has_invoices or has_credit_notes):
                continue

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
                "conceptos_totales": conceptos_list,
                "clientes_totales": clientes_list,
                "moves": moves,
            })

        # La sede completa solo se muestra si le quedó al menos un diario con datos.
        if wh_block["journals"]:
            groups.append(wh_block)

    # 7) Neto del período actual (ventas brutas + NC negativas)
    grand_net = {
        "count_invoices": grand["count_invoices"] + grand_refunds["count_invoices"],
        "subtotal_untaxed": grand["subtotal_untaxed"] + grand_refunds["subtotal_untaxed"],
        "total_sales": grand["total_sales"] + grand_refunds["total_sales"],
    }

    # 8) Período anterior — misma duración, desplazado atrás
    prev_from, prev_to = _get_previous_period_dates(date_from, date_to)
    prev_inv = _get_grand_totals_fast(journals, prev_from, prev_to, "out_invoice", negate=False, advisor_name=advisor_name, **_kw)
    prev_ref = _get_grand_totals_fast(journals, prev_from, prev_to, "out_refund", negate=True, advisor_name=advisor_name, **_kw)
    prev_net = {
        "count_invoices": prev_inv["count_invoices"] + prev_ref["count_invoices"],
        "subtotal_untaxed": prev_inv["subtotal_untaxed"] + prev_ref["subtotal_untaxed"],
        "total_sales": prev_inv["total_sales"] + prev_ref["total_sales"],
    }

    # 9) Diario seleccionado (para UI)
    selected_journal = None
    if j_id:
        j = request.env["account.journal"].sudo().browse(j_id)
        if j.exists():
            selected_journal = {"id": j.id, "name": j.name}

    # 10) Sección gráfica — reutiliza los mismos `journals` (misma sede,
    # diario, empresas permitidas y equipo/asesor/estado) para que sus
    # totales coincidan siempre con los de `grand_net` de arriba.
    sales_analytics = analytics.get_sales_analytics(
        journals, date_from, date_to, advisor_name=advisor_name, team_id=t_id, state_filter=state_filter,
    )

    return {
        "ok": True,
        "date_from": date_from,
        "date_to": date_to,
        "selected_journal": selected_journal,
        "selected_advisor": advisor_name,
        "warehouses": [{"id": w.id, "name": w.name} for w in warehouses],
        "journals": [{"id": j.id, "name": j.name} for j in journals],
        "grand": grand,
        "grand_refunds": grand_refunds,
        "grand_net": grand_net,
        "previous_period": {
            "date_from": prev_from,
            "date_to": prev_to,
            "grand": prev_inv,
            "grand_refunds": prev_ref,
            "grand_net": prev_net,
        },
        "groups": groups,
        "analytics": sales_analytics,
    }
