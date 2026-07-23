from odoo import models, fields, api

class AccountAccountFilter(models.Model):
    _inherit = 'account.account'

    long_numeric_code = fields.Boolean(
        string='Código numérico ≥ 8',
        compute='_compute_long_numeric_code',
        store=True,
        index=True,
        help='Verdadero si el código es solo dígitos y longitud >= 8.',
        readonly=False,
        tracking=True
    )

    @api.depends('code', 'deprecated')
    def _compute_long_numeric_code(self):
        for rec in self:
            code = (rec.code or '').strip()
            rec.long_numeric_code = code.isdigit() and len(code) >= 8
