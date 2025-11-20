from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ParkingAuthorizedVehicle(models.Model):
    _name = 'parking.authorized.vehicle'
    _description = 'Placas Autorizadas por Contrato'
    _order = 'contract_id, vehicle_number'
    _rec_name = 'vehicle_number'

    contract_id = fields.Many2one(
        'parking.monthly.contract',
        string='Personal Autorizado',
        required=True,
        ondelete='cascade',
        index=True,
        help='Contrato mensual al que pertenece esta placa.'
    )
    site_id = fields.Many2one(
        related='contract_id.site_id',
        string='Sede',
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        related='contract_id.partner_id',
        string='Contacto',
        store=True,
        readonly=True,
    )
    vehicle_number = fields.Char(
        string='Placa',
        required=True,
        help='Placa del vehículo autorizada.'
    )
    vehicle_number_normalized = fields.Char(
        string='Placa (Normalizada)',
        help='Versión normalizada de la placa para búsquedas.',
        index=True,
        copy=False,
    )
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Si está desactivado, esta placa no se considerará autorizada.'
    )

    _sql_constraints = [
        ('unique_plate_per_contract',
         'unique(contract_id, vehicle_number_normalized)',
         'Esta placa ya está registrada en este contrato.'),
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

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        # Ensure contract_id is set when creating from a contract context
        if 'contract_id' in fields_list and not defaults.get('contract_id'):
            ctx = self.env.context
            default_contract = ctx.get('default_contract_id')
            if not default_contract and ctx.get('active_model') == 'parking.monthly.contract':
                default_contract = ctx.get('active_id')
            if default_contract:
                defaults['contract_id'] = default_contract
        return defaults
