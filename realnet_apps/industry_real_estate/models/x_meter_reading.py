from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime

class XMeterReading(models.Model):
    _name = 'x.meter.reading'
    _description = 'Meter Reading'
    _order = 'x_date asc, id asc'

    x_account_analytic_account_id = fields.Many2one('account.analytic.account', required=True, ondelete='cascade')
    x_meter_id = fields.Many2one(
        comodel_name='x.meter', 
        string='Medidor', 
        required=True,
        ondelete='cascade',
        index=True,
    )
    x_description = fields.Char("Descripción")
    x_date = fields.Date(string="Fecha de lectura", required=True)
    # Mes (YYYY-MM) calculado a partir de x_date, pero editable
    x_month = fields.Char(
        string='Mes',
        compute='_compute_month',
        inverse='_inverse_month',
        store=True,
        index=True,
        help='Formato: YYYY-MM (ej: 2025-10). Al editar, se ajustará x_date al primer día del mes.'
    )
    x_quantity = fields.Float(string='Lectura', required=True, default=0.0)
    x_usage = fields.Float(string='Uso', default=0.0)
    x_invoice_id = fields.Many2one('account.move', string='Factura', readonly=True)

    # Moneda y costos tomados en el momento de la importación
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='x_account_analytic_account_id.company_id.currency_id',
        store=True,
        readonly=True,
    )
    x_unit_cost = fields.Monetary(
        string='Costo unitario',
        currency_field='currency_id',
        help='Costo por unidad. Se autocompleta desde la configuración del medidor, '
             'pero puede editarse manualmente o establecerse desde importación.'
    )
    x_usage_cost = fields.Monetary(
        string='Costo uso',
        currency_field='currency_id',
        compute='_compute_usage_cost',
        store=True,
        help='Uso x Costo unitario (COP).'
    )

    @api.model_create_multi
    def create(self, vals_list):
        # Autocompletar x_unit_cost desde configuración si no se proporciona
        for vals in vals_list:
            if 'x_unit_cost' not in vals and 'x_meter_id' in vals:
                # Obtener el medidor para acceder a su precio (x_price)
                # x_price es computed y trae el precio desde res.company según meter_type
                meter = self.env['x.meter'].browse(vals['x_meter_id'])
                if meter:
                    # meter.x_price ya tiene el precio correcto desde res.company
                    vals['x_unit_cost'] = meter.x_price or 0.0

        recs = super().create(vals_list)
        recs._recompute_usage_batch()
        return recs

    def write(self, vals):
        res = super().write(vals)
        # Solo recalcular si cambiaron campos que afectan el cálculo de uso
        # NO recalcular si el usuario editó x_usage manualmente
        should_recompute = (
            'x_quantity' in vals or
            'x_date' in vals or
            'x_account_analytic_account_id' in vals or
            'x_meter_id' in vals
        )
        if should_recompute and not self.env.context.get('_skip_usage_recompute'):
            self._recompute_usage_batch()
        return res

    def _recompute_usage_batch(self):
        groups = {}
        for r in self:
            key = (r.x_account_analytic_account_id.id, r.x_meter_id.id)
            groups.setdefault(key, r.env[self._name])
            groups[key] |= r
        for (acc_id, meter_id), _ in groups.items():
            mrs = self.search([
                ('x_account_analytic_account_id', '=', acc_id),
                ('x_meter_id', '=', meter_id),
            ], order='x_date asc, id asc')
            prev_qty = None
            writes = []
            for mr in mrs:
                # Si es la primera lectura (prev_qty is None):
                # - Si ya tiene x_usage definido por el usuario, respetarlo
                # - Si no, establecer en 0.0
                if prev_qty is None:
                    usage = float(mr.x_usage or 0.0)  # Respeta el valor manual
                else:
                    # Para lecturas subsiguientes, calcular como diferencia
                    usage = float(mr.x_quantity or 0.0) - float(prev_qty or 0.0)

                if (mr.x_usage or 0.0) != usage:
                    writes.append((mr, usage))
                prev_qty = mr.x_quantity or 0.0
            for mr, usage in writes:
                mr.with_context(_skip_usage_recompute=True).write({'x_usage': usage})

    @api.depends('x_usage', 'x_unit_cost')
    def _compute_usage_cost(self):
        for r in self:
            if not r.exists():
                continue
            r.x_usage_cost = (r.x_usage or 0.0) * (r.x_unit_cost or 0.0)

    @api.depends('x_date')
    def _compute_month(self):
        for r in self:
            if not r.exists():
                continue
            if r.x_date:
                r.x_month = r.x_date.strftime('%Y-%m')
            else:
                r.x_month = False
    def _inverse_month(self):
        """Permite editar x_month y ajusta x_date al primer día del mes especificado"""
        for r in self:
            if not r.x_month:
                # Si x_month está vacío, no hacemos nada (o podrías limpiar x_date)
                continue

            # Validar formato YYYY-MM
            try:
                # Intentar parsear el mes ingresado
                month_date = datetime.strptime(r.x_month, '%Y-%m')
                # Establecer x_date al primer día del mes
                r.x_date = month_date.date()
            except ValueError:
                raise UserError(
                    f"Formato de mes inválido: '{r.x_month}'. "
                    "Use el formato YYYY-MM (ej: 2025-10)"
                )

    @api.onchange('x_quantity', 'x_date', 'x_account_analytic_account_id', 'x_meter_id')
    def _onchange_calculate_usage(self):
        """
        Calcula x_usage en tiempo real cuando el usuario cambia la lectura o fecha.
        Se ejecuta en la interfaz ANTES de guardar para dar feedback inmediato.
        """
        # Solo calcular si tenemos los datos mínimos
        if not self.x_date or not self.x_account_analytic_account_id or not self.x_meter_id:
            return

        # Buscar la lectura anterior del mismo medidor en la misma propiedad
        prev_reading = self.env['x.meter.reading'].search([
            ('x_account_analytic_account_id', '=', self.x_account_analytic_account_id.id),
            ('x_meter_id', '=', self.x_meter_id.id),
            ('x_date', '<', self.x_date),
            ('id', '!=', self.id or False),  # Excluir el registro actual (si ya existe)
        ], order='x_date desc, id desc', limit=1)

        if prev_reading:
            # Hay lectura anterior: calcular diferencia automáticamente
            calculated_usage = float(self.x_quantity or 0.0) - float(prev_reading.x_quantity or 0.0)
            self.x_usage = calculated_usage

            # Opcional: Mostrar warning si el uso es negativo
            if calculated_usage < 0:
                return {
                    'warning': {
                        'title': 'Uso Negativo',
                        'message': f'El uso calculado es negativo ({calculated_usage:.2f}). '
                                   f'La lectura actual ({self.x_quantity}) es menor que la anterior ({prev_reading.x_quantity}).'
                    }
                }
        # Si no hay lectura anterior (primera lectura), dejar x_usage como está (manual)

    @api.onchange('x_meter_id')
    def _onchange_meter_unit_cost(self):
        """
        Autocompletar x_unit_cost cuando se selecciona un medidor.
        Se ejecuta en la interfaz para dar feedback inmediato.
        """
        if self.x_meter_id and not self.x_unit_cost:
            # Solo autocompletar si x_unit_cost está vacío
            # meter.x_price trae el precio desde res.company según meter_type
            self.x_unit_cost = self.x_meter_id.x_price or 0.0
