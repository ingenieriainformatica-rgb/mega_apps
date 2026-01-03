# -*- coding: utf-8 -*-
import logging
from odoo import http  #type: ignore
from .services.sales import (  #type: ignore
    get_sales_data,
)
from .services.utils import (  #type: ignore
    get_active_warehouses,
)

_logger = logging.getLogger(__name__)


class SalesControllerDashboard(http.Controller):

    @http.route('/mega_dashboard/sales/statistics', type='json', auth='user')
    def get_sales_statistics(self, **kw):
        date_from = kw.get("date_from")
        date_to = kw.get("date_to")
        warehouse_id = kw.get("warehouse_id")
        try:
            return {"sales": get_sales_data(date_from=date_from, date_to=date_to, warehouse_id=warehouse_id)}
        except Exception as e:
            _logger.error(f"Error getting sales statistics: {str(e)}")
            return {'error': 'Failed to fetch sales statistics'}

    @http.route("/mega_dashboard/get/warehouses", type="json", auth="user")
    def get_warehouses(self, **kw):
        try:
            return {
                "ok": True,
                "items": [{"id": wh.id, "name": wh.name} for wh in get_active_warehouses()],
            }
        except Exception as e:
            _logger.error(f"Error getting warehouses: {str(e)}")
            return {'error': 'Failed to fetch warehouses'}