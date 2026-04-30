from odoo import fields, models  # type: ignore


class FleetVehicleModel(models.Model):
    _inherit = "fleet.vehicle.model"

    show_on_website = fields.Boolean(
        string="Mostrar en Website",
        default=False,
        help="Si está activo, este modelo se mostrará en el sitio web."
    )
