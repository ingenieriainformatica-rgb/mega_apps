from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ecoerp_ok = fields.Boolean(string='ECOERP', help='Campo para gestión de inventario de propiedades', default=True)
    contract_title = fields.Html(string='Titulo del contrato')
    clause_line_ids = fields.One2many(
        'clause.line',
        'template_id',
        string='Cláusulas'
    )

    # Campos adicionales para categorización
    item_category = fields.Selection([
        ('furniture', 'Muebles'),
        ('kitchen', 'Utensilios de Cocina'),
        ('electronics', 'Electrónicos'),
        ('decoration', 'Decoración'),
        ('appliances', 'Electrodomésticos'),
        ('tools', 'Herramientas'),
        ('other', 'Otros')
    ], string='Categoría de Item')
    
    property_item_ids = fields.One2many('property.item', 'product_id')
    total_in_properties = fields.Integer('Total en Propiedades', compute='_compute_total_in_properties')

    @api.depends('property_item_ids')
    def _compute_total_in_properties(self):
        """
        Calcula el total de items de este producto en todas las propiedades.
        Cuenta cuántas veces aparece este producto en property.item.
        """
        for template in self:
            # Contar todos los property.item que referencian este product_id
            template.total_in_properties = len(template.property_item_ids)