import logging
from odoo import models, fields, api  # type: ignore

_logger = logging.getLogger(__name__)


class SaleReport(models.Model):
    _inherit = "sale.report"

    vehicle = fields.Char(string="Vehículo", readonly=True)

    @api.model
    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        # 's' = sale_order (alias en el SQL del sale.report)
        res["vehicle"] = "s.vehicle"
        return res

    @api.model
    def _group_by_sale(self):
        # Debe ir en group by porque sale.report agrupa resultados
        return super()._group_by_sale() + ", s.vehicle"