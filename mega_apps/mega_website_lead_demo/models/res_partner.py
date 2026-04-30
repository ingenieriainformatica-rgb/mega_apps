from odoo import fields, models  # type: ignore


class ResPartner(models.Model):
    _inherit = "res.partner"

    accept_web_terms_conditions = fields.Boolean(
        string="Acepta términos y condiciones desde la web",
        help="Indica si el contacto aceptó términos y condiciones desde el formulario web.",
        default=False,
    )
