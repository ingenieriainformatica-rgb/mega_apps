import logging
from odoo import models  # type: ignore

_logger = logging.getLogger(__name__)


class FleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'

    def name_get(self):
        _logger.info('\n\n\n Executing name_get for FleetVehicleModeln \n\n\n')
        result = []
        for record in self:
            result.append((record.id, record.name or ''))
        return result
