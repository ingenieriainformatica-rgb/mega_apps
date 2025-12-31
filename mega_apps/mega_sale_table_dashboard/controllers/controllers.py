# -*- coding: utf-8 -*-
import logging
from odoo import http  #type: ignore
from .services.utils import (  #type: ignore
    get_sales_data,
)

_logger = logging.getLogger(__name__)


class SalesControllerDashboard(http.Controller):

    @http.route('/sales/statistics', type='json', auth='user')
    def get_sales_statistics(self, **kw):
        date_from = kw.get("date_from")
        date_to = kw.get("date_to")
        try:
            return {"sales": get_sales_data(date_from=date_from, date_to=date_to)}
        except Exception as e:
            _logger.error(f"Error getting sales statistics: {str(e)}")
            return {'error': 'Failed to fetch sales statistics'}
        