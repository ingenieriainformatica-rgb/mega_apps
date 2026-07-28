# -*- coding: utf-8 -*-
import logging
from odoo import http  # type: ignore
from .services.sales import (  # type: ignore
    get_sales_data,
)
from .services.utils import get_active_warehouses, get_sale_journals, get_advisors  # type: ignore

_logger = logging.getLogger(__name__)


class SalesControllerDashboard(http.Controller):

    @http.route("/mega_dashboard/sales/statistics", type="json", auth="user")
    def get_sales_statistics(self, **kw):
        date_from = kw.get("date_from")
        date_to = kw.get("date_to")
        warehouse_id = kw.get("warehouse_id")
        journal_id = kw.get("journal_id")
        advisor_id = kw.get("advisor_id")
        try:
            return {
                "sales": get_sales_data(
                    date_from=date_from,
                    date_to=date_to,
                    warehouse_id=warehouse_id,
                    journal_id=journal_id,
                    advisor_id=advisor_id,
                )
            }
        except Exception as e:
            _logger.error(f"Error getting sales statistics: {str(e)}")
            return {"error": "Failed to fetch sales statistics"}

    @http.route("/mega_dashboard/get/advisors", type="json", auth="user")
    def get_advisors_route(self, **kw):
        try:
            return {
                "ok": True,
                "items": [
                    {"id": p.id, "name": p.name} for p in get_advisors()
                ],
            }
        except Exception as e:
            _logger.error(f"Error getting advisors: {str(e)}")
            return {"error": "Failed to fetch advisors"}

    @http.route("/mega_dashboard/get/warehouses", type="json", auth="user")
    def get_warehouses(self, **kw):
        try:
            return {
                "ok": True,
                "items": [
                    {"id": wh.id, "name": wh.name} for wh in get_active_warehouses()
                ],
            }
        except Exception as e:
            _logger.error(f"Error getting warehouses: {str(e)}")
            return {"error": "Failed to fetch warehouses"}

    @http.route("/mega_dashboard/get/journals", type="json", auth="user")
    def get_journals(self, **kw):
        warehouse_id = kw.get("warehouse_id")
        try:
            # ✅ NORMALIZAR warehouse_id
            if isinstance(warehouse_id, dict):
                warehouse_id = warehouse_id.get("id")
            elif isinstance(warehouse_id, list):
                warehouse_id = warehouse_id[0] if warehouse_id else None
            return {
                "ok": True,
                "items": [
                    {"id": j.id, "name": j.name}
                    for j in get_sale_journals(warehouse_id)
                ],
            }
        except Exception as e:
            _logger.exception("Error getting journals")
            return {
                "ok": False,
                "error": str(e),
            }
