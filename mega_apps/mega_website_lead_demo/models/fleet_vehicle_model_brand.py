from odoo import models, fields  # type: ignore


class FleetVehicleModelBrand(models.Model):
    _inherit = 'fleet.vehicle.model.brand'

    show_on_website = fields.Boolean(
        string="Mostrar en Website",
        default=False
    )
