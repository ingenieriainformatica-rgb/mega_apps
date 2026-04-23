import logging
from odoo import models, fields  #type: ignore

_logger = logging.getLogger(__name__)


class CrmServiceType(models.Model):
    _name = 'crm.service.type'
    _description = 'Tipo de Servicio'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True)
    active = fields.Boolean(default=True)
    description = fields.Text(string='Descripción')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'El servicio ya existe.')
    ]
