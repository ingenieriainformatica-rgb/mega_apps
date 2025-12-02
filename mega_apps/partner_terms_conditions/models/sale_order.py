from odoo import api, models

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.onchange("partner_id")
    def _onchange_partner_terms_conditions(self):
        if self.partner_id:
            if not self.partner_id.has_terms_conditions:
                self.note = False
            else:
                terms = self.env["ir.config_parameter"].sudo().get_param(
                    "sale.default_terms_conditions"
                )
                if terms:
                    self.note = terms
