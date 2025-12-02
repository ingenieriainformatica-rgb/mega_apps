from odoo import fields, models

class ResPartner(models.Model):
    _inherit = "res.partner"

    has_terms_conditions = fields.Boolean(
        string="Aplicar términos y condiciones",
        default=True,
        help="Si está desmarcado, las facturas y ventas de este cliente no mostrarán términos y condiciones."
    )
