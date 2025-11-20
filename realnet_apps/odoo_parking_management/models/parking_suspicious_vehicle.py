from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ParkingSuspiciousVehicle(models.Model):
    _name = 'parking.suspicious.vehicle'
    _description = 'Vehículos Sospechosos'
    _order = 'vehicle_number'
    _rec_name = 'vehicle_number'

    vehicle_number = fields.Char(
        string='Placa',
        required=True,
        help='Placa del vehículo a alertar.'
    )
    vehicle_number_normalized = fields.Char(
        string='Placa (Normalizada)',
        index=True,
        copy=False,
        help='Versión normalizada de la placa (mayúsculas, sin espacios).'
    )
    reason = fields.Text(
        string='Motivo',
        required=True,
        help='Motivo de la alerta para este vehículo.'
    )
    apply_to_all_sites = fields.Boolean(
        string='Todas las sedes',
        default=False,
        help='Si está activo, la alerta aplica en todas las sedes.'
    )
    site_ids = fields.Many2many(
        'parking.site',
        'parking_suspicious_site_rel',
        'suspicious_id', 'site_id',
        string='Sedes',
        help='Una o varias sedes donde aplica la alerta (si no aplica a todas).',
    )
    print_ticket = fields.Boolean(
        string='Imprimir Tiquete',
        default=True,
        help='Si está activo, solo muestra alerta informativa. Si está desactivado, bloquea el registro de la entrada.'
    )
    active = fields.Boolean(
        string='Activo',
        default=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True,
        help='Compañía a la que pertenece la alerta.'
    )

    _sql_constraints = [
        # Evitar registros duplicados exactos por placa normalizada y compañía
        ('unique_plate_company',
         'unique(vehicle_number_normalized, company_id)',
         'Ya existe una alerta para esta placa en la compañía.'),
    ]

    @api.model
    def _normalize_plate(self, plate):
        if not plate:
            return False
        return ''.join(str(plate).upper().strip().split())

    @api.onchange('vehicle_number')
    def _onchange_vehicle_number(self):
        if self.vehicle_number:
            self.vehicle_number = self.vehicle_number.strip()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('vehicle_number'):
                vals['vehicle_number_normalized'] = self._normalize_plate(vals['vehicle_number'])
        return super().create(vals_list)

    def write(self, vals):
        if 'vehicle_number' in vals:
            vals['vehicle_number_normalized'] = self._normalize_plate(vals.get('vehicle_number'))
        return super().write(vals)
