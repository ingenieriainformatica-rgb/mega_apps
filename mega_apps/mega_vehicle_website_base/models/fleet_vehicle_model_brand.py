from odoo import fields, models  # type: ignore


class FleetVehicleModelBrand(models.Model):
    _inherit = "fleet.vehicle.model.brand"

    show_on_website = fields.Boolean(
        string="Mostrar en Website",
        default=False,
        help="Si está activo, esta marca se mostrará en el sitio web.",
    )
