import logging
from odoo import models, fields  # type: ignore

_logger = logging.getLogger(__name__)


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    engine_number = fields.Char(
        string="Número de motor",
        help="Número de motor del vehículo."
    )
