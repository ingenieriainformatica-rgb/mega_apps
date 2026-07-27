# -*- coding: utf-8 -*-
import logging
from odoo import models, fields  #type: ignore

_logger = logging.getLogger(__name__)


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    show_in_sales_dashboard = fields.Boolean(
        string="Mostrar en informe (Tablero)",
        default=False,
        help="Si está activado, este almacén aparecerá en el Informe Contabilidad / Informes.",
    )
