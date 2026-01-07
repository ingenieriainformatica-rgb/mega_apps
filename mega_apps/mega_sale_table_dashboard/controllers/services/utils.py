import logging
from odoo.http import request  # type: ignore

_logger = logging.getLogger(__name__)


def get_active_warehouses(warehouse_id=None):
    Warehouse = request.env["stock.warehouse"].sudo()
    company = request.env.company

    domain = [
        ("company_id", "=", company.id),
        ("show_in_sales_dashboard", "=", True),
    ]

    if warehouse_id:
        domain.append(("id", "=", int(warehouse_id)))

    warehouses = Warehouse.search(domain, order="name")

    _logger.info(
        "Warehouses dashboard -> ids=%s",
        warehouses.ids
    )

    return warehouses
