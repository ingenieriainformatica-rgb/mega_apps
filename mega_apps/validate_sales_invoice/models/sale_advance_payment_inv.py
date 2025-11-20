import logging
from odoo import api, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def create_invoices(self):
        # Si intentan usar anticipo, también bloqueamos hasta entregar
        orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
        for order in orders:
            order._check_all_delivered()
        return super().create_invoices()
