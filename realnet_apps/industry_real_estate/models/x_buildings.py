

from odoo import models, fields, api


class X_Buildings(models.Model):
    _name = 'x_buildings'
    _description = 'Edificios'
    _rec_name = 'x_name'  # Este campo muestra el nombre del edificio

    x_name = fields.Char(string='Nombre del Edificio', required=True)
    x_address = fields.Char(string='Dirección', required=True)
    x_city = fields.Char(string='Ciudad', required=False)
    x_department = fields.Char(string='Departamento', required=False)

    property_features = fields.Many2many('x_property.feature', string='Características de la propiedad')
    
    