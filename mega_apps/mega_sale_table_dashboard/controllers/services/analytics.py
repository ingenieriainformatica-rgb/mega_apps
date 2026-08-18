# -*- coding: utf-8 -*-
"""
Agregaciones para la sección gráfica del tablero (KPIs, ventas por asesor,
ventas por empresa+asesor, evolución temporal y distribución adicional).

Fuente de datos: account.move (misma fuente que la tabla "Facturado" ya
existente en sales.py), para que las cifras de las tarjetas/gráficas nuevas
coincidan exactamente con las de la tabla. Ver README/CONTEXT del módulo
para la discusión de por qué no se usó sale.order.

Todas las agregaciones se hacen con read_group (o, para la distribución por
categoría de producto -que exige agrupar por un campo relacionado que
read_group no soporta como groupby-, con una consulta SQL parametrizada de
solo lectura). No se cargan recordsets completos de account.move/account.move.line.
"""
import logging
from collections import defaultdict
from datetime import date as date_cls, timedelta
from odoo.http import request  # type: ignore
from .utils import state_domain  # type: ignore

_logger = logging.getLogger(__name__)

JOURNAL_WH_FIELD = "warehouse_ids"

# Documentos considerados en las gráficas: facturas (suman) y notas
# crédito (restan) contabilizadas. Igual que en sales.py.
_MOVE_TYPES = (("out_invoice", 1.0), ("out_refund", -1.0))


def _base_domain(journals, date_from=None, date_to=None, move_type=None, advisor_name=None, team_id=None, state_filter=None):
    domain = [
        ("journal_id", "in", journals.ids),
    ] + state_domain(state_filter)
    if move_type:
        domain.append(("move_type", "=", move_type))
    else:
        domain.append(("move_type", "in", ("out_invoice", "out_refund")))
    if date_from:
        domain.append(("invoice_date", ">=", date_from))
    if date_to:
        domain.append(("invoice_date", "<=", date_to))
    if advisor_name:
        domain.append(("mega_concepto", "=ilike", advisor_name))
    if team_id:
        domain.append(("team_id", "=", int(team_id)))
    return domain


def _prefixed_state_domain(prefix, state_filter):
    """Igual que state_domain() pero para dominios sobre un campo
    relacionado (p.ej. account.move.line filtrando por move_id.state)."""
    return [(f"{prefix}.{field}", op, value) for field, op, value in state_domain(state_filter)]


def _grouped_net_totals(journals, groupby_fields, date_from=None, date_to=None, advisor_name=None, team_id=None, state_filter=None):
    """Totales NETOS (facturas - notas crédito) agrupados por groupby_fields.
    Devuelve dict: tuple(claves) -> {"count", "subtotal", "total", "labels": {campo: etiqueta}}.
    El conteo de documentos es la suma de ambos tipos (no se resta), igual
    que grand_net en sales.py; solo los montos llevan signo.
    """
    if not journals:
        return {}

    Move = request.env["account.move"].sudo()
    out = defaultdict(lambda: {"count": 0, "subtotal": 0.0, "total": 0.0, "labels": {}})

    for move_type, sign in _MOVE_TYPES:
        domain = _base_domain(journals, date_from, date_to, move_type, advisor_name, team_id, state_filter)
        rows = Move.read_group(
            domain=domain,
            fields=["amount_untaxed:sum", "amount_total:sum"] + groupby_fields,
            groupby=groupby_fields,
            lazy=False,
        )
        for r in rows:
            key = []
            labels = {}
            for f in groupby_fields:
                v = r.get(f)
                if isinstance(v, (list, tuple)):
                    key.append(v[0])
                    labels[f] = v[1]
                else:
                    key.append(v)
                    labels[f] = v
            key = tuple(key)
            bucket = out[key]
            bucket["labels"] = labels
            bucket["count"] += int(r.get("__count", 0) or 0)
            bucket["subtotal"] += float(r.get("amount_untaxed", 0.0) or 0.0) * sign
            bucket["total"] += float(r.get("amount_total", 0.0) or 0.0) * sign

    return out


def _get_general_kpis(journals, date_from=None, date_to=None, advisor_name=None, team_id=None, state_filter=None):
    totals = _grouped_net_totals(journals, [], date_from, date_to, advisor_name, team_id, state_filter)
    row = next(iter(totals.values()), {"count": 0, "subtotal": 0.0, "total": 0.0})

    count = row["count"]
    total_sales = row["total"]
    subtotal = row["subtotal"]
    avg_per_doc = (total_sales / count) if count else 0.0

    # Clientes distintos (facturas + NC) en el período/filtro.
    Move = request.env["account.move"].sudo()
    partner_rows = Move.read_group(
        domain=_base_domain(journals, date_from, date_to, None, advisor_name, team_id, state_filter) + [("partner_id", "!=", False)],
        fields=["partner_id"],
        groupby=["partner_id"],
        lazy=False,
    )
    client_count = len(partner_rows)

    # Unidades vendidas netas (líneas de producto reales, sin secciones/notas).
    MoveLine = request.env["account.move.line"].sudo()
    total_qty = 0.0
    for move_type, sign in _MOVE_TYPES:
        line_domain = [
            ("move_id.journal_id", "in", journals.ids),
            ("move_id.move_type", "=", move_type),
            ("display_type", "=", "product"),
        ] + _prefixed_state_domain("move_id", state_filter)
        if date_from:
            line_domain.append(("move_id.invoice_date", ">=", date_from))
        if date_to:
            line_domain.append(("move_id.invoice_date", "<=", date_to))
        if advisor_name:
            line_domain.append(("move_id.mega_concepto", "=ilike", advisor_name))
        if team_id:
            line_domain.append(("move_id.team_id", "=", int(team_id)))

        qty_rows = MoveLine.read_group(
            domain=line_domain,
            fields=["quantity:sum"],
            groupby=[],
            lazy=False,
        )
        if qty_rows:
            total_qty += float(qty_rows[0].get("quantity", 0.0) or 0.0) * sign

    return {
        "total_sales": total_sales,
        "subtotal_untaxed": subtotal,
        "count_docs": count,
        "client_count": client_count,
        "avg_per_doc": avg_per_doc,
        "total_qty": total_qty,
    }


def _get_advisor_breakdown(journals, date_from=None, date_to=None, advisor_name=None, team_id=None, state_filter=None):
    totals = _grouped_net_totals(journals, ["mega_concepto"], date_from, date_to, advisor_name, team_id, state_filter)
    rows = []
    for key, v in totals.items():
        name = (v["labels"].get("mega_concepto") or "").strip() or "Sin asesor"
        rows.append({
            "advisor": name,
            "total_sales": v["total"],
            "subtotal_untaxed": v["subtotal"],
            "count_docs": v["count"],
            "avg_per_doc": (v["total"] / v["count"]) if v["count"] else 0.0,
        })
    rows.sort(key=lambda r: r["total_sales"], reverse=True)
    return rows


def _get_client_advisor_breakdown(journals, date_from=None, date_to=None, advisor_name=None, team_id=None, state_filter=None, max_clients=15):
    """Ventas por cliente ("empresa" facturada, p.ej. rentings, aseguradoras,
    flotas corporativas) y asesor. Confirmado con datos reales: el 0% de la
    facturación queda "Sin cliente" -el hallazgo anterior de que "todo caía
    en Sin cliente" era un bug propio (ver _get_warehouse_advisor_breakdown
    de una iteración anterior, ya no existe), no un problema real de datos.
    Se limita a los `max_clients` con más facturación dentro del filtro
    activo (sede/diario/asesor/fecha) para no enviar cientos de clientes al
    navegador -con un filtro de sede muy específico puede haber cientos de
    clientes distintos, cada uno con pocas compras-.
    """
    totals = _grouped_net_totals(journals, ["partner_id", "mega_concepto"], date_from, date_to, advisor_name, team_id, state_filter)

    client_totals = defaultdict(float)
    client_names = {}
    for key, v in totals.items():
        # El id relacional va en `key` (la llave del agrupado); en
        # `v["labels"]` para un campo relacional ya viene el NOMBRE, no
        # una tupla (id, nombre) -por eso sirve tal cual para mostrar-.
        p_id = key[0] or 0
        p_name = v["labels"].get("partner_id") or "Sin cliente"
        client_totals[p_id] += v["total"]
        client_names[p_id] = p_name

    top_client_ids = set(sorted(client_totals, key=lambda pid: client_totals[pid], reverse=True)[:max_clients])

    rows = []
    for key, v in totals.items():
        p_id = key[0] or 0
        if p_id not in top_client_ids:
            continue
        advisor = (v["labels"].get("mega_concepto") or "").strip() or "Sin asesor"
        rows.append({
            "client": client_names.get(p_id, "Sin cliente"),
            "advisor": advisor,
            "total_sales": v["total"],
            "count_docs": v["count"],
        })
    rows.sort(key=lambda r: r["total_sales"], reverse=True)
    return rows


def _get_top_products(journals, date_from=None, date_to=None, advisor_name=None, team_id=None, state_filter=None, limit=30, kind=None):
    """Top productos más vendidos por cantidad neta (facturado - NC).
    kind=None -> todo (productos + servicios mezclados, como antes).
    kind='service' -> solo servicios (mano de obra, etc.), product.type='service'.
    kind='storable' -> solo bienes con inventario real, product.type='consu'
    y is_storable=True (quedan afuera los 'consu' no almacenables -p.ej.
    algún cargo varios sin control de stock-, que en este negocio son una
    fracción pequeña; no encajan en ninguna de las dos categorías pedidas).
    """
    if not journals:
        return []

    MoveLine = request.env["account.move.line"].sudo()
    totals = defaultdict(lambda: {"qty": 0.0, "revenue": 0.0})

    for move_type, sign in _MOVE_TYPES:
        domain = [
            ("move_id.journal_id", "in", journals.ids),
            ("move_id.move_type", "=", move_type),
            ("display_type", "=", "product"),
        ] + _prefixed_state_domain("move_id", state_filter)
        if kind == "service":
            domain.append(("product_id.type", "=", "service"))
        elif kind == "storable":
            domain.append(("product_id.type", "=", "consu"))
            domain.append(("product_id.is_storable", "=", True))
        if date_from:
            domain.append(("move_id.invoice_date", ">=", date_from))
        if date_to:
            domain.append(("move_id.invoice_date", "<=", date_to))
        if advisor_name:
            domain.append(("move_id.mega_concepto", "=ilike", advisor_name))
        if team_id:
            domain.append(("move_id.team_id", "=", int(team_id)))

        rows = MoveLine.read_group(
            domain=domain,
            fields=["quantity:sum", "price_subtotal:sum", "product_id"],
            groupby=["product_id"],
            lazy=False,
        )
        for r in rows:
            product = r.get("product_id")
            if not product:
                continue
            p_id, p_name = product
            bucket = totals[p_id]
            bucket["name"] = p_name
            bucket["qty"] += float(r.get("quantity", 0.0) or 0.0) * sign
            bucket["revenue"] += float(r.get("price_subtotal", 0.0) or 0.0) * sign

    items = [
        {"product": v.get("name", ""), "qty": v["qty"], "revenue": v["revenue"]}
        for v in totals.values() if v["qty"]
    ]
    items.sort(key=lambda x: x["qty"], reverse=True)
    return items[:limit]


def _pick_granularity(date_from, date_to):
    try:
        d_from = date_cls.fromisoformat(str(date_from))
        d_to = date_cls.fromisoformat(str(date_to))
    except (ValueError, TypeError):
        return "month"
    span = (d_to - d_from).days + 1
    if span <= 31:
        return "day"
    if span <= 180:
        return "week"
    return "month"


def _get_timeseries(journals, date_from=None, date_to=None, advisor_name=None, team_id=None, state_filter=None):
    if not journals or not date_from or not date_to:
        return {"granularity": "day", "points": []}

    granularity = _pick_granularity(date_from, date_to)
    groupby_key = "invoice_date:%s" % granularity

    Move = request.env["account.move"].sudo()
    buckets = defaultdict(lambda: {"total": 0.0, "subtotal": 0.0, "count": 0})

    for move_type, sign in _MOVE_TYPES:
        domain = _base_domain(journals, date_from, date_to, move_type, advisor_name, team_id, state_filter)
        rows = Move.read_group(
            domain=domain,
            fields=["amount_untaxed:sum", "amount_total:sum"],
            groupby=[groupby_key],
            lazy=False,
        )
        for r in rows:
            range_info = (r.get("__range") or {}).get(groupby_key) or {}
            bucket_from = range_info.get("from")
            if not bucket_from:
                continue
            bucket_from = str(bucket_from)[:10]  # normaliza a YYYY-MM-DD
            b = buckets[bucket_from]
            b["count"] += int(r.get("__count", 0) or 0)
            b["subtotal"] += float(r.get("amount_untaxed", 0.0) or 0.0) * sign
            b["total"] += float(r.get("amount_total", 0.0) or 0.0) * sign

    points = [
        {"date": k, "total_sales": v["total"], "subtotal_untaxed": v["subtotal"], "count_docs": v["count"]}
        for k, v in buckets.items()
    ]
    points.sort(key=lambda p: p["date"])
    return {"granularity": granularity, "points": points}


def _get_distribution(journals, date_from=None, date_to=None, advisor_name=None, team_id=None, state_filter=None):
    dist = {
        "by_warehouse": [],
        "by_team": [],
        "by_doc_type": [],
        "by_category": [],
    }

    # ── Por sede: reutiliza el mapeo journal -> warehouse ya resuelto ────
    j_wh = {j.id: (getattr(j, JOURNAL_WH_FIELD).ids or [None])[0] for j in journals}
    j_wh_name = {j.id: (getattr(j, JOURNAL_WH_FIELD)[:1].name or "") for j in journals}
    totals_by_journal = _grouped_net_totals(journals, ["journal_id"], date_from, date_to, advisor_name, team_id, state_filter)
    wh_acc = defaultdict(lambda: {"total": 0.0, "count": 0})
    for key, v in totals_by_journal.items():
        jid = key[0]
        wh_id = j_wh.get(jid)
        if not wh_id:
            continue
        b = wh_acc[wh_id]
        b["total"] += v["total"]
        b["count"] += v["count"]
        b["name"] = j_wh_name.get(jid, "")
    dist["by_warehouse"] = sorted(
        [{"label": v.get("name", ""), "total_sales": v["total"], "count_docs": v["count"]} for v in wh_acc.values()],
        key=lambda r: r["total_sales"], reverse=True,
    )

    # ── Por equipo de venta ───────────────────────────────────────────
    totals_by_team = _grouped_net_totals(journals, ["team_id"], date_from, date_to, advisor_name, team_id, state_filter)
    rows = []
    for key, v in totals_by_team.items():
        # El nombre del equipo sí vive en `labels` (ahí "team_id" ya es el
        # nombre, ver _grouped_net_totals); lo que había mal antes era
        # tratarlo como si fuera la tupla (id, nombre) sin serlo.
        name = (v["labels"].get("team_id") or "").strip() or "Sin equipo"
        rows.append({"label": name, "total_sales": v["total"], "count_docs": v["count"]})
    rows.sort(key=lambda r: r["total_sales"], reverse=True)
    dist["by_team"] = rows

    # ── Por tipo de documento (Factura vs Nota crédito) ─────────────────
    Move = request.env["account.move"].sudo()
    doc_rows = []
    labels_map = {"out_invoice": "Facturas", "out_refund": "Notas crédito"}
    for move_type, _sign in _MOVE_TYPES:
        domain = _base_domain(journals, date_from, date_to, move_type, advisor_name, team_id, state_filter)
        r = Move.read_group(domain=domain, fields=["amount_total:sum"], groupby=[], lazy=False)
        total = float(r[0].get("amount_total", 0.0) or 0.0) if r else 0.0
        count = int(r[0].get("__count", 0) or 0) if r else 0
        if count:
            doc_rows.append({"label": labels_map[move_type], "total_sales": total, "count_docs": count})
    dist["by_doc_type"] = doc_rows

    # ── Por categoría de producto (SQL de solo lectura, parametrizada) ──
    # read_group no soporta agrupar por un campo relacionado (categ_id
    # vive en product.template, no en account.move.line), y agrupar por
    # product_id primero traería miles de filas intermedias (~8.6k
    # productos distintos) solo para reducirlas después en Python. Una
    # consulta agregada evita ese intermedio; sigue respetando el mismo
    # filtro (diarios ya resueltos según sede/empresa permitidas) y no
    # se expone a input del usuario sin parametrizar.
    if journals and "mega_concepto" in request.env["account.move"]._fields:
        # Estado: se elige entre 3 fragmentos fijos definidos en Python
        # (nunca se interpola texto libre del usuario en el SQL).
        if not state_filter or state_filter == "posted":
            state_sql = "am.state NOT IN ('draft', 'cancel')"
        elif state_filter == "all":
            state_sql = "TRUE"
        elif state_filter in ("draft", "cancel"):
            state_sql = "am.state = %(state_filter)s"
        else:
            state_sql = "am.state NOT IN ('draft', 'cancel')"

        cr = request.env.cr
        cr.execute(
            """
            SELECT pc.complete_name AS category,
                   SUM(CASE WHEN am.move_type = 'out_invoice' THEN aml.quantity ELSE -aml.quantity END) AS qty,
                   SUM(CASE WHEN am.move_type = 'out_invoice' THEN aml.price_subtotal ELSE -aml.price_subtotal END) AS subtotal
              FROM account_move_line aml
              JOIN account_move am ON am.id = aml.move_id
              JOIN product_product pp ON pp.id = aml.product_id
              JOIN product_template pt ON pt.id = pp.product_tmpl_id
              JOIN product_category pc ON pc.id = pt.categ_id
             WHERE am.journal_id = ANY(%(journal_ids)s)
               AND (""" + state_sql + """)
               AND am.move_type IN ('out_invoice', 'out_refund')
               AND aml.display_type = 'product'
               AND (%(date_from)s IS NULL OR am.invoice_date >= %(date_from)s)
               AND (%(date_to)s IS NULL OR am.invoice_date <= %(date_to)s)
               AND (%(advisor)s IS NULL OR am.mega_concepto ILIKE %(advisor)s)
               AND (%(team_id)s IS NULL OR am.team_id = %(team_id)s)
             GROUP BY pc.complete_name
             ORDER BY subtotal DESC
             LIMIT 15
            """,
            {
                "journal_ids": journals.ids,
                "date_from": date_from or None,
                "date_to": date_to or None,
                "advisor": advisor_name or None,
                "team_id": int(team_id) if team_id else None,
                "state_filter": state_filter if state_filter in ("draft", "cancel") else None,
            },
        )
        dist["by_category"] = [
            {"label": r[0] or "Sin categoría", "qty": float(r[1] or 0.0), "subtotal_untaxed": float(r[2] or 0.0)}
            for r in cr.fetchall()
        ]

    return dist


def get_sales_analytics(journals, date_from=None, date_to=None, advisor_name=None, team_id=None, state_filter=None):
    """Punto de entrada único: arma todos los bloques de la sección
    gráfica reutilizando los mismos `journals` ya resueltos por
    get_sales_data() (sede + diario + empresas permitidas), para que los
    totales coincidan siempre con los de la tabla. `state_filter` viaja
    hasta cada sub-consulta -antes se ignoraba aquí y toda la sección
    gráfica quedaba fija en "posted" sin importar lo que el usuario
    eligiera en el filtro de Estado-."""
    return {
        "kpis": _get_general_kpis(journals, date_from, date_to, advisor_name, team_id, state_filter),
        "by_advisor": _get_advisor_breakdown(journals, date_from, date_to, advisor_name, team_id, state_filter),
        "by_client_advisor": _get_client_advisor_breakdown(journals, date_from, date_to, advisor_name, team_id, state_filter),
        "timeseries": _get_timeseries(journals, date_from, date_to, advisor_name, team_id, state_filter),
        "distribution": _get_distribution(journals, date_from, date_to, advisor_name, team_id, state_filter),
        "top_products": _get_top_products(journals, date_from, date_to, advisor_name, team_id, state_filter, kind="storable"),
        "top_services": _get_top_products(journals, date_from, date_to, advisor_name, team_id, state_filter, kind="service"),
    }
