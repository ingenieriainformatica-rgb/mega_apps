import logging
from odoo import models, fields  #type: ignore

_logger = logging.getLogger(__name__)


class CrmHomeYear(models.Model):
    _name = 'crm.lead.year'
    _description = 'Año del vehículo'
    _order = 'year desc'
    _rec_name = 'year'

    year = fields.Integer(string='Año', required=True)

    _sql_constraints = [
        ('year_unique', 'unique(year)', 'El año ya existe.')
    ]
