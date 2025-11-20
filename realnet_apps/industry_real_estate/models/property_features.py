

from odoo import models, fields, api

class PropertyFeature(models.Model):
    _name = 'x_property.feature'
    _description = 'Caracteristicas de la propiedad'

    name = fields.Char(string='Caracteristicas')
    
    
    

    # def write(self, vals):
    #     for record in self:
    #         old_vals = record.owner_line_ids  # Copia segura
            

    #         res = super(AccountAnalyticAccount, record).write(vals)

    #         if 'owner_line_ids' in vals:
    #             record.property_owner_change_report(old_vals, vals['owner_line_ids'])

    #     return True