import logging
from odoo.http import request  # type: ignore

_logger = logging.getLogger(__name__)


def get_active_warehouses():
    Warehouse = request.env["stock.warehouse"].sudo()
    company = request.env.company

    excluded_ids = [4] # Example: Exclude warehouse with ID 4: GRUPOMEGA
    domain = [
        ("company_id", "=", company.id),
        ("id", "not in", excluded_ids),
    ]
    return Warehouse.search(domain, order="name")
