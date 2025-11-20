from odoo import models, fields, api

class XMeter(models.Model):
    _name = 'x.meter'
    _description = 'Meter'

    name = fields.Char(string="Nombre", required=True)
    meter_type = fields.Selection([
        ('energy', 'Energía'),
        ('water', 'Agua'),
        ('sanitation', 'Saneamiento'),
        ('misc', 'Varios'),
    ], string='Tipo de Medidor', required=True)

    x_price = fields.Float(
        string='Precio por unidad',
        compute='_compute_price_from_company',
        inverse='_inverse_price_to_company',
        store=False,
        help="Precio configurado en la compañía actual"
    )
    product_id = fields.Many2one('product.product', string='Producto (opcional)')

    @api.depends('meter_type')
    @api.depends_context('company')
    def _compute_price_from_company(self):
        """Obtiene el precio desde la configuración de la compañía."""
        company = self.env.company
        price_mapping = {
            'energy': company.utility_price_energy,
            'water': company.utility_price_water,
            'sanitation': company.utility_price_sanitation,
            'misc': company.utility_price_misc,
        }
        for meter in self:
            meter.x_price = price_mapping.get(meter.meter_type, 0.0)

    def _inverse_price_to_company(self):
        """Escribe el precio en la configuración de la compañía."""
        company = self.env.company
        for meter in self:
            if meter.meter_type == 'energy':
                company.utility_price_energy = meter.x_price
            elif meter.meter_type == 'water':
                company.utility_price_water = meter.x_price
            elif meter.meter_type == 'sanitation':
                company.utility_price_sanitation = meter.x_price
            elif meter.meter_type == 'misc':
                company.utility_price_misc = meter.x_price
