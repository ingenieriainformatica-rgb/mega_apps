import logging
from odoo import models, fields  #type: ignore

_logger = logging.getLogger(__name__)


class CrmHomeZone(models.Model):
    _name = 'crm.home.zone'
    _description = 'Zona de Domicilio'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True)
    active = fields.Boolean(default=True)
    description = fields.Text(string='Descripción')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'El nombre ya existe.')
    ]
