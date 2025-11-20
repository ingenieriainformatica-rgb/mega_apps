




from odoo import models, fields

class ReceptionTemplate(models.Model):
    _name = 'reception.template'
    _description = 'Plantilla de Recepción'

    title       = fields.Text(string="Titulo", readonly=False)
    images      = fields.Binary(string="Imagenes", readonly=False)
    state       = fields.Boolean(string="estado", readonly=False)