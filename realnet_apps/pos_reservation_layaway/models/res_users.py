from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Compatibility field used by some label/printing add-ons
    print_label_report_id = fields.Many2one(
        'ir.actions.report',
        string='Default Label Report'
    )

