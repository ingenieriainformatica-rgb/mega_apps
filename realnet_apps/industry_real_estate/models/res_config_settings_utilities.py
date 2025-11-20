from odoo import fields, models


class ResConfigSettingsUtilities(models.TransientModel):
    _inherit = 'res.config.settings'

    # Servicios Públicos (precios por unidad)
    utility_price_energy = fields.Float(
        string='Precio Energía',
        related='company_id.utility_price_energy',
        readonly=False,
    )
    utility_price_water = fields.Float(
        string='Precio Agua',
        related='company_id.utility_price_water',
        readonly=False,
    )
    utility_price_sanitation = fields.Float(
        string='Precio Saneamiento',
        related='company_id.utility_price_sanitation',
        readonly=False,
    )
    utility_price_misc = fields.Float(
        string='Precio Varios',
        related='company_id.utility_price_misc',
        readonly=False,
    )

