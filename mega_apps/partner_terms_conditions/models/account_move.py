from odoo import api, models

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("partner_id")
    def _onchange_partner_terms_conditions(self):
        if self.partner_id:
            if not self.partner_id.has_terms_conditions:
                self.narration = False
            else:
                terms = self.env["ir.config_parameter"].sudo().get_param(
                    "account.default_terms_conditions"
                )
                if terms:
                    self.narration = terms
