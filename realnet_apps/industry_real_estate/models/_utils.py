from odoo import models

class EcoERPUtils(models.AbstractModel):
    _name = 'eco_erp.utils'
    _description = "Helps ECOERP"

    def get_ecoerp_settings(self):
        IC = self.env['ir.config_parameter'].sudo()
        admin_pct = float(IC.get_param('eco_erp.default_admin_percent', default=10.0))
        product_canon = self.env['product.product'].browse(int(IC.get_param('eco_erp.product_canon_id') or 0))
        product_owner = self.env['product.product'].browse(int(IC.get_param('eco_erp.product_owner_payment_id') or 0))
        return {
            'admin_pct': admin_pct,
            'product_canon': product_canon,
            'product_owner': product_owner,
        }