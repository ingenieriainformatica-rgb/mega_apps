# -*- coding: utf-8 -*-
from odoo import fields, models #type: ignore


class FleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'

    vehicle_type = fields.Selection(
        selection_add=[
            ('truck', 'Camión'),
            ('bus', 'Bus'),
            ('van', 'Camioneta'),
            ('machinery', 'Maquinaria'),
        ],
        ondelete={
            'truck': 'set default',
            'bus': 'set default',
            'van': 'set default',
            'machinery': 'set default',
        },
    )
    vehicle_range = fields.Integer(string="Kilometraje")
