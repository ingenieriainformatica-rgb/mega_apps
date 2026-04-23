import logging
from odoo import models, fields, api  # type: ignore

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    tipo_servicio_id = fields.Many2one(
        'crm.service.type',
        string='Tipo de Servicio'
    )

    zona_domicilio_id = fields.Many2one(
        'crm.home.zone',
        string='Zona de Domicilio'
    )

    year_vehicule_id = fields.Many2one(
        'crm.lead.year',
        string='Año de fabricación del vehículo'
    )

    brand_id = fields.Many2one(
        'fleet.vehicle.model.brand',
        string='Marca del vehículo'
    )

    modelo_id = fields.Many2one(
        'fleet.vehicle.model',
        string='Modelo del vehículo',
        domain="[('brand_id', '=', brand_id)]"
    )

    accept_terms = fields.Boolean(
        string='Acepta términos y condiciones'
    )

    service_address = fields.Char(
        string='Dirección del servicio',
    )

    license_plate = fields.Char(
        string='Placa del vehículo'
    )

    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        self.modelo_id = False
