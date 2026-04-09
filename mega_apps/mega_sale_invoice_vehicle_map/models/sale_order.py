import logging
from odoo import models  #type:ignore

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _prepare_invoice(self):
        _logger.info(f"\n\n\nPreparing invoice for sale order {self.name}\n\n\n")
        self.ensure_one()
        vals = super()._prepare_invoice()
        vals.update({
            'vehicle': self.vehicle or False,
        })
        return vals
