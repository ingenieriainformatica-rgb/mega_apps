# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ParkingOperationalDashboard(models.TransientModel):
    """Tablero operativo unificado (Mensualidades + Ordinarios) sin métricas monetarias"""
    _name = 'parking.operational.dashboard'
    _description = 'Tablero Operativo del Parqueadero'

    # Selección de sedes
    site_id = fields.Many2one(
        'parking.site',
        string='Sitio de Parqueo',
        help='Sede principal (opcional si se seleccionan varias)'
    )
    site_ids = fields.Many2many(
        'parking.site',
        string='Sedes',
        help='Seleccione una o varias sedes para agregar métricas'
    )
    all_sites = fields.Boolean(
        string='Todas las sedes',
        default=True,
        help='Si está marcado, se incluirán todas las sedes permitidas para el usuario'
    )

    # Rango de fechas para KPIs históricos
    date_from = fields.Date(string='Desde', default=fields.Date.today, required=True)
    date_to = fields.Date(string='Hasta', default=fields.Date.today, required=True)

    # KPIs de ocupación actual
    total_slots_count = fields.Integer(string='Total de Cupos', compute='_compute_metrics')
    occupied_slots_count = fields.Integer(string='Cupos Ocupados', compute='_compute_metrics')
    occupancy_rate = fields.Float(string='Ocupación (%)', compute='_compute_metrics')

    occupied_moto_count = fields.Integer(string='Motos en Parqueo', compute='_compute_metrics')
    occupied_auto_count = fields.Integer(string='Autos en Parqueo', compute='_compute_metrics')
    occupancy_rate_moto = fields.Float(string='Ocupación Motos (%)', compute='_compute_metrics')
    occupancy_rate_auto = fields.Float(string='Ocupación Autos (%)', compute='_compute_metrics')

    active_now_count = fields.Integer(string='Vehículos Dentro Ahora', compute='_compute_metrics')

    # KPIs de flujo y tiempos (periodo)
    entries_count_period_total = fields.Integer(string='Entradas en el Periodo', compute='_compute_metrics')
    entries_count_monthly_period = fields.Integer(string='Entradas Mensualidades', compute='_compute_metrics')
    entries_count_regular_period = fields.Integer(string='Entradas Ordinarias', compute='_compute_metrics')

    avg_duration_hours_all = fields.Float(string='Tiempo Promedio (h)', compute='_compute_metrics')
    avg_duration_hours_monthly = fields.Float(string='Promedio Mensualidades (h)', compute='_compute_metrics')
    avg_duration_hours_regular = fields.Float(string='Promedio Ordinarios (h)', compute='_compute_metrics')
    avg_duration_hours_moto = fields.Float(string='Promedio Motos (h)', compute='_compute_metrics')
    avg_duration_hours_auto = fields.Float(string='Promedio Autos (h)', compute='_compute_metrics')

    # KPIs de sobreestancia
    overstay_count = fields.Integer(string='Sobreestancias', compute='_compute_metrics')
    overstay_rate = fields.Float(string='Tasa Sobreestancia (%)', compute='_compute_metrics')

    # Rotación
    rotation_period = fields.Float(string='Rotación (periodo)', compute='_compute_metrics', help='Entradas/espacio en el periodo')
    rotation_daily_per_space = fields.Float(string='Rotación diaria por cupo', compute='_compute_metrics')

    # Pico de ocupación
    peak_occupancy_rate = fields.Float(string='Ocupación Pico (%)', compute='_compute_metrics')
    peak_occupancy_hour = fields.Char(string='Hora Pico', compute='_compute_metrics')

    # Tiempos de proceso (minutos)
    avg_entry_time_mins = fields.Float(string='Tiempo Prom. Ingreso (min)', compute='_compute_metrics')
    avg_exit_payment_time_mins = fields.Float(string='Tiempo Prom. Salida→Pago (min)', compute='_compute_metrics')

    # Métodos de pago (share)
    payments_digital_pct = fields.Float(string='% Pagos Digitales', compute='_compute_metrics')
    payments_cash_pct = fields.Float(string='% Pagos Efectivo', compute='_compute_metrics')
    payments_digital_count = fields.Integer(string='Pagos Digitales', compute='_compute_metrics')
    payments_cash_count = fields.Integer(string='Pagos Efectivo', compute='_compute_metrics')

    @api.depends('site_id', 'site_ids', 'all_sites', 'date_from', 'date_to')
    def _compute_metrics(self):
        for rec in self:
            sites = rec._selected_site_ids()
            # Reset
            rec.total_slots_count = 0
            rec.occupied_slots_count = 0
            rec.occupancy_rate = 0
            rec.occupied_moto_count = 0
            rec.occupied_auto_count = 0
            rec.occupancy_rate_moto = 0
            rec.occupancy_rate_auto = 0
            rec.active_now_count = 0
            rec.entries_count_period_total = 0
            rec.entries_count_monthly_period = 0
            rec.entries_count_regular_period = 0
            rec.avg_duration_hours_all = 0
            rec.avg_duration_hours_monthly = 0
            rec.avg_duration_hours_regular = 0
            rec.avg_duration_hours_moto = 0
            rec.avg_duration_hours_auto = 0
            rec.overstay_count = 0
            rec.overstay_rate = 0
            rec.rotation_period = 0
            rec.rotation_daily_per_space = 0
            rec.peak_occupancy_rate = 0
            rec.peak_occupancy_hour = ''
            rec.avg_entry_time_mins = 0
            rec.avg_exit_payment_time_mins = 0
            rec.payments_digital_pct = 0
            rec.payments_cash_pct = 0
            rec.payments_digital_count = 0
            rec.payments_cash_count = 0

            if not sites:
                continue

            # Ocupación actual a partir de slots
            Slot = self.env['slot.details']
            slots = Slot.search([('site_id', 'in', sites)])
            total = len(slots)
            occupied = len(slots.filtered(lambda s: not s.is_available))

            # Desglose por tipo (Moto/Auto)
            moto_slots = slots.filtered(lambda s: (s.slot_type_id.vehicle_type or '').lower().startswith('moto'))
            auto_slots = slots.filtered(lambda s: (s.slot_type_id.vehicle_type or '').lower().startswith('auto'))
            occ_moto = len(moto_slots.filtered(lambda s: not s.is_available))
            occ_auto = len(auto_slots.filtered(lambda s: not s.is_available))

            rec.total_slots_count = total
            rec.occupied_slots_count = occupied
            # Para widget percentage, devolver razón (0..1)
            rec.occupancy_rate = (occupied / total) if total else 0.0
            rec.occupied_moto_count = occ_moto
            rec.occupied_auto_count = occ_auto
            rec.occupancy_rate_moto = (occ_moto / len(moto_slots)) if moto_slots else 0.0
            rec.occupancy_rate_auto = (occ_auto / len(auto_slots)) if auto_slots else 0.0

            # Vehículos dentro ahora desde parking.entry
            Entry = self.env['parking.entry']
            active_now = Entry.search([('site_id', 'in', sites), ('state', '=', 'check_in')])
            rec.active_now_count = len(active_now)

            # Rango de fechas para histórico
            dt_from = datetime.combine(rec.date_from, datetime.min.time()) if rec.date_from else None
            dt_to = datetime.combine(rec.date_to, datetime.max.time()) if rec.date_to else None

            domain_period = [('site_id', 'in', sites), ('created_date', '>=', dt_from), ('created_date', '<=', dt_to)]
            entries_period = Entry.search(domain_period)
            rec.entries_count_period_total = len(entries_period)
            monthly = entries_period.filtered(lambda e: e.is_monthly)
            regular = entries_period.filtered(lambda e: not e.is_monthly)
            rec.entries_count_monthly_period = len(monthly)
            rec.entries_count_regular_period = len(regular)

            # Promedios de duración (en horas)
            def avg(vals):
                return sum(vals) / len(vals) if vals else 0.0

            durations_all = [e.duration for e in entries_period if e.duration]
            durations_monthly = [e.duration for e in monthly if e.duration]
            durations_regular = [e.duration for e in regular if e.duration]
            durations_moto = [e.duration for e in entries_period if e.duration and e.slot_type_id and (e.slot_type_id.vehicle_type or '').lower().startswith('moto')]
            durations_auto = [e.duration for e in entries_period if e.duration and e.slot_type_id and (e.slot_type_id.vehicle_type or '').lower().startswith('auto')]

            rec.avg_duration_hours_all = avg(durations_all)
            rec.avg_duration_hours_monthly = avg(durations_monthly)
            rec.avg_duration_hours_regular = avg(durations_regular)
            rec.avg_duration_hours_moto = avg(durations_moto)
            rec.avg_duration_hours_auto = avg(durations_auto)

            # Sobreestancia vs allowed_park_duration (slot.type)
            overstay = 0
            considered = 0
            for e in entries_period:
                if e.duration and e.slot_type_id and e.slot_type_id.allowed_park_duration:
                    considered += 1
                    if e.duration > e.slot_type_id.allowed_park_duration:
                        overstay += 1
            rec.overstay_count = overstay
            rec.overstay_rate = (overstay / considered) if considered else 0.0

            # Rotación
            days = max(1, (rec.date_to - rec.date_from).days + 1)
            rec.rotation_period = (rec.entries_count_period_total / total) if total else 0.0
            rec.rotation_daily_per_space = (rec.entries_count_period_total / (total * days)) if total else 0.0

            # Tiempo de ingreso (creación → check_in) y salida→pago
            entry_times = []
            exit_pay_times = []
            for e in entries_period:
                if e.created_date and e.check_in:
                    entry_times.append((e.check_in - e.created_date).total_seconds() / 60.0)
                if e.check_out:
                    pay_dt = None
                    if e.payment_id and getattr(e.payment_id, 'date', None):
                        # account.payment.date es Date; considerar a medianoche
                        pay_dt = datetime.combine(e.payment_id.date, datetime.min.time())
                    elif e.invoice_id and getattr(e.invoice_id, 'invoice_date', None):
                        pay_dt = datetime.combine(e.invoice_id.invoice_date, datetime.min.time())
                    if pay_dt:
                        diff = (pay_dt - e.check_out).total_seconds() / 60.0
                        if diff >= 0:
                            exit_pay_times.append(diff)
            rec.avg_entry_time_mins = avg(entry_times)
            rec.avg_exit_payment_time_mins = avg(exit_pay_times)

            # Pagos digitales vs efectivo (por entradas del periodo)
            payments = entries_period.mapped('payment_id')
            cash = 0
            digital = 0
            for p in payments:
                jtype = getattr(p.journal_id, 'type', False)
                if jtype == 'cash':
                    cash += 1
                elif jtype in ('bank', 'general'):  # bank como digital; general por si usan diarios de banco general
                    digital += 1
            total_pay = cash + digital
            rec.payments_cash_count = cash
            rec.payments_digital_count = digital
            rec.payments_cash_pct = (cash / total_pay) if total_pay else 0.0
            rec.payments_digital_pct = (digital / total_pay) if total_pay else 0.0

            # Pico de ocupación (aproximación por entradas/salidas por hora netas)
            # Construimos una serie por hora con net_flow = check_ins - check_outs acumulado
            checkins = Entry.read_group([
                ('site_id', 'in', sites), ('created_date', '>=', dt_from), ('created_date', '<=', dt_to)
            ], ['id:count'], ['created_date:hour'])
            checkouts = Entry.read_group([
                ('site_id', 'in', sites), ('check_out', '>=', dt_from), ('check_out', '<=', dt_to)
            ], ['id:count'], ['check_out:hour'])
            # Mapear a dict {hour_str: count}
            def to_map(rows, key):
                m = {}
                for r in rows:
                    # Odoo puede devolver 'id_count' o '__count' segan versin/config
                    cnt = r.get('id_count', r.get('__count', 0))
                    m[str(r.get(key))] = cnt
                return m
            ins_map = to_map(checkins, 'created_date:hour')
            outs_map = to_map(checkouts, 'check_out:hour')
            # Recorremos horas presentes; calculamos ocupación relativa acumulada desde 0
            hours = sorted(set(list(ins_map.keys()) + list(outs_map.keys())))
            occ = 0
            peak = 0
            peak_hour = ''
            for h in hours:
                occ += ins_map.get(h, 0) - outs_map.get(h, 0)
                if total:
                    rate = (occ / total)
                    if rate > peak:
                        peak = rate
                        peak_hour = h
            rec.peak_occupancy_rate = peak
            rec.peak_occupancy_hour = peak_hour

    @api.model
    def get_site_domain(self):
        return self.env.user.get_user_parking_sites_domain()

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'site_id' in fields_list and not defaults.get('site_id'):
            default_site = self.env.user.get_default_parking_site()
            if default_site:
                defaults['site_id'] = default_site.id
        return defaults

    def _selected_site_ids(self):
        self.ensure_one()
        if self.all_sites:
            ids = self.env.user.allowed_parking_site_ids.ids
            if ids:
                return ids
            return self.env['parking.site'].search([]).ids
        if self.site_ids:
            return self.site_ids.ids
        if self.site_id:
            return [self.site_id.id]
        return []

    # Acciones rápidas
    def action_view_entries_period(self):
        self.ensure_one()
        dt_from = datetime.combine(self.date_from, datetime.min.time()) if self.date_from else None
        dt_to = datetime.combine(self.date_to, datetime.max.time()) if self.date_to else None
        return {
            'name': _('Entradas del Periodo'),
            'type': 'ir.actions.act_window',
            'res_model': 'parking.entry',
            'view_mode': 'graph,list,form',
            'domain': [
                ('site_id', 'in', self._selected_site_ids()),
                ('created_date', '>=', dt_from),
                ('created_date', '<=', dt_to),
            ],
        }

    def action_view_flow_by_hour(self):
        self.ensure_one()
        dt_from = datetime.combine(self.date_from, datetime.min.time()) if self.date_from else None
        dt_to = datetime.combine(self.date_to, datetime.max.time()) if self.date_to else None
        return {
            'name': _('Flujo por Hora (Entradas)'),
            'type': 'ir.actions.act_window',
            'res_model': 'parking.entry',
            'view_mode': 'graph,list',
            'views': [(self.env.ref('odoo_parking_management.parking_entry_graph_by_hour').id, 'graph')],
            'domain': [('site_id', 'in', self._selected_site_ids()), ('created_date', '>=', dt_from), ('created_date', '<=', dt_to)],
        }

    def action_view_checkout_by_hour(self):
        self.ensure_one()
        dt_from = datetime.combine(self.date_from, datetime.min.time()) if self.date_from else None
        dt_to = datetime.combine(self.date_to, datetime.max.time()) if self.date_to else None
        return {
            'name': _('Flujo por Hora (Salidas)'),
            'type': 'ir.actions.act_window',
            'res_model': 'parking.entry',
            'view_mode': 'graph,list',
            'views': [(self.env.ref('odoo_parking_management.parking_entry_graph_checkout_by_hour').id, 'graph')],
            'domain': [('site_id', 'in', self._selected_site_ids()), ('check_out', '>=', dt_from), ('check_out', '<=', dt_to)],
        }

    def action_view_duration_by_vehicle(self):
        self.ensure_one()
        dt_from = datetime.combine(self.date_from, datetime.min.time()) if self.date_from else None
        dt_to = datetime.combine(self.date_to, datetime.max.time()) if self.date_to else None
        return {
            'name': _('Duración por Tipo de Vehículo'),
            'type': 'ir.actions.act_window',
            'res_model': 'parking.entry',
            'view_mode': 'graph,list',
            'views': [(self.env.ref('odoo_parking_management.parking_entry_graph_duration_by_vehicle').id, 'graph')],
            'domain': [('site_id', 'in', self._selected_site_ids()), ('created_date', '>=', dt_from), ('created_date', '<=', dt_to)],
        }

    def action_view_payments_share(self):
        self.ensure_one()
        dt_from = datetime.combine(self.date_from, datetime.min.time()) if self.date_from else None
        dt_to = datetime.combine(self.date_to, datetime.max.time()) if self.date_to else None
        entries = self.env['parking.entry'].search([
            ('site_id', 'in', self._selected_site_ids()),
            ('created_date', '>=', dt_from),
            ('created_date', '<=', dt_to),
            ('payment_id', '!=', False),
        ])
        payment_ids = entries.mapped('payment_id').ids
        return {
            'name': _('Pagos por Diario'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'graph,list',
            'views': [(self.env.ref('odoo_parking_management.account_payment_graph_by_journal').id, 'graph')],
            'domain': [('id', 'in', payment_ids)],
        }

    def action_view_overstays(self):
        self.ensure_one()
        dt_from = datetime.combine(self.date_from, datetime.min.time()) if self.date_from else None
        dt_to = datetime.combine(self.date_to, datetime.max.time()) if self.date_to else None
        entries = self.env['parking.entry'].search([
            ('site_id', 'in', self._selected_site_ids()),
            ('created_date', '>=', dt_from),
            ('created_date', '<=', dt_to),
        ])
        overstay_ids = entries.filtered(lambda e: e.duration and e.slot_type_id and e.slot_type_id.allowed_park_duration and e.duration > e.slot_type_id.allowed_park_duration).ids
        return {
            'name': _('Sobreestancias del Periodo'),
            'type': 'ir.actions.act_window',
            'res_model': 'parking.entry',
            'view_mode': 'list,form',
            'domain': [('id', 'in', overstay_ids)],
            'context': {},
        }
