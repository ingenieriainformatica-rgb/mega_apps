import logging
from odoo.http import request  # type: ignore

JOURNAL_WH_FIELD = "warehouse_ids"
JOURNAL_TYPE = "sale"
WH_ACTIVE_FIELD = "show_in_sales_dashboard"
ALL_HEADQUARTERS = "allHeadquarters"

_logger = logging.getLogger(__name__)


def get_active_warehouses(warehouse_id=None):
    Warehouse = request.env["stock.warehouse"].sudo()
    Journal = request.env["account.journal"].sudo()
    company = request.env.company

    # 1) Warehouses que realmente tienen diarios de venta mapeados
    mapped_wh_ids = Journal.search([
        ("company_id", "=", company.id),
        ("type", "=", JOURNAL_TYPE),
        (JOURNAL_WH_FIELD, "!=", False),
    ]).mapped(JOURNAL_WH_FIELD).ids  # flatten de M2M

    domain = [
        ("company_id", "=", company.id),
        ("show_in_sales_dashboard", "=", True),
        ("id", "in", mapped_wh_ids),   # ✅ solo los que tienen diario
    ]

    # 2) Si mandan una sede específica
    if warehouse_id and warehouse_id != ALL_HEADQUARTERS:
        domain.append(("id", "=", int(warehouse_id)))

    warehouses = Warehouse.search(domain, order="name")

    _logger.info("Warehouses dashboard (filtered by journals) -> ids=%s", warehouses.ids)
    return warehouses


def get_sale_journals(warehouse_id=None):
    Journal = request.env["account.journal"].sudo()
    Warehouse = request.env["stock.warehouse"].sudo()
    company = request.env.company

    # 1) Warehouses activos (los que deben salir en dashboard)
    active_whs = Warehouse.search([
        ("company_id", "=", company.id),
        (WH_ACTIVE_FIELD, "=", True),
    ])
    active_wh_ids = active_whs.ids

    domain = [
        ("company_id", "=", company.id),
        ("type", "=", JOURNAL_TYPE),
        # 2) Solo journals que tengan relación con warehouses ACTIVOS
        (JOURNAL_WH_FIELD, "in", active_wh_ids),
    ]

    # 3) Si mandan sede específica, filtra por ese warehouse (siempre que no sea "Todos")
    if warehouse_id and warehouse_id != ALL_HEADQUARTERS:
        wid = int(warehouse_id)
        # si el warehouse no está activo, no debe traer nada
        if wid not in active_wh_ids:
            return Journal.browse([])  # vacío
        domain.append((JOURNAL_WH_FIELD, "in", [wid]))

    journals = Journal.search(domain, order="name")
    return journals
