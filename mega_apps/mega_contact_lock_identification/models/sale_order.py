# -*- coding: utf-8 -*-
from odoo import models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        for order in self:
            order.partner_id.commercial_partner_id._check_mega_commercial_identification(
                _("confirmar el pedido %s", order.name)
            )
        return super().action_confirm()
