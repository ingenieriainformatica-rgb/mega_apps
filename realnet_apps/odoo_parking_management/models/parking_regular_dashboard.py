# -*- coding: utf-8 -*-
import logging
from datetime import date, datetime, timedelta
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ParkingRegularDashboard(models.TransientModel):
    """Dashboard para clientes ordinarios (no mensualidades)"""
    _name = 'parking.regular.dashboard'
    _description = 'Tablero Clientes Ordinarios'

    site_id = fields.Many2one(
        'parking.site',
        string='Sitio de Parqueo',
        required=False,
        help='Sede para las métricas del tablero'
    )
    site_ids = fields.Many2many(
        'parking.site',
        string='Sedes',
        help='Seleccione una o varias sedes para agregar métricas'
    )
    all_sites = fields.Boolean(
        string='Todas las sedes',
        help='Si está marcado, se incluirán todas las sedes permitidas para el usuario',
        default=True
    )
    date_from = fields.Date(
        string='Desde',
        required=True,
        default=fields.Date.today,
        help='Fecha inicial para calcular métricas'
    )
    date_to = fields.Date(
        string='Hasta',
        required=True,
        default=fields.Date.today,
        help='Fecha final para calcular métricas'
    )

    # Métricas generales
    total_entries_count = fields.Integer(
        string='Entradas Totales',
        compute='_compute_metrics'
    )
    active_now_count = fields.Integer(
        string='En Parqueo',
        compute='_compute_metrics'
    )
    invoiced_amount = fields.Monetary(
        string='Facturado',
        compute='_compute_metrics'
    )
    paid_amount = fields.Monetary(
        string='Pagado',
        compute='_compute_metrics'
    )
    pending_payment_count = fields.Integer(
        string='Pagos Pendientes',
        compute='_compute_metrics'
    )

    # Métricas por tipo de vehículo (según slot_type)
    moto_entries_count = fields.Integer(
        string='Motos',
        compute='_compute_metrics'
    )
    auto_entries_count = fields.Integer(
        string='Automóviles',
        compute='_compute_metrics'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('site_id', 'site_ids', 'all_sites', 'date_from', 'date_to')
    def _compute_metrics(self):
        for dashboard in self:
            dashboard.total_entries_count = 0
            dashboard.active_now_count = 0
            dashboard.invoiced_amount = 0
            dashboard.paid_amount = 0
            dashboard.pending_payment_count = 0
            dashboard.moto_entries_count = 0
            dashboard.auto_entries_count = 0

            site_ids = dashboard._selected_site_ids()
            if not site_ids:
                continue

            # Rango de fechas (convertir a datetimes de inicio/fin de día)
            dt_from = datetime.combine(dashboard.date_from, datetime.min.time()) if dashboard.date_from else None
            dt_to = datetime.combine(dashboard.date_to, datetime.max.time()) if dashboard.date_to else None

            # Entradas ordinarias del periodo (no mensuales)
            domain = [
                ('site_id', 'in', site_ids),
                ('created_date', '>=', dt_from),
                ('created_date', '<=', dt_to),
                ('is_monthly', '=', False),
            ]
            entries = self.env['parking.entry'].search(domain)

            dashboard.total_entries_count = len(entries)

            # En parqueo ahora (independiente del rango, pero filtrado por sede)
            active_now = self.env['parking.entry'].search([
                ('site_id', 'in', site_ids),
                ('state', '=', 'check_in')
            ])
            dashboard.active_now_count = len(active_now)

            # Facturación del periodo a partir de invoices vinculadas a las entradas
            posted_entries = entries.filtered(lambda e: e.invoice_id and e.invoice_id.state == 'posted')
            dashboard.invoiced_amount = sum(posted_entries.mapped('invoice_id.amount_total'))

            paid_entries = posted_entries.filtered(lambda e: e.invoice_id.payment_state == 'paid')
            dashboard.paid_amount = sum(paid_entries.mapped('invoice_id.amount_total'))

            pending_payment = posted_entries.filtered(lambda e: e.invoice_id.payment_state != 'paid')
            dashboard.pending_payment_count = len(pending_payment)

            # Conteos por tipo de vehículo
            dashboard.moto_entries_count = len(entries.filtered(
                lambda e: e.slot_type_id and (e.slot_type_id.vehicle_type or '').lower().startswith('moto')
            ))
            dashboard.auto_entries_count = len(entries.filtered(
                lambda e: e.slot_type_id and (e.slot_type_id.vehicle_type or '').lower().startswith('auto')
            ))

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

    # Acciones
    def action_view_entries_period(self):
        self.ensure_one()
        dt_from = datetime.combine(self.date_from, datetime.min.time()) if self.date_from else None
        dt_to = datetime.combine(self.date_to, datetime.max.time()) if self.date_to else None
        site_ids = self._selected_site_ids()
        return {
            'name': _('Entradas del Periodo'),
            'type': 'ir.actions.act_window',
            'res_model': 'parking.entry',
            'view_mode': 'list,form',
            'domain': [
                ('site_id', 'in', site_ids),
                ('is_monthly', '=', False),
                ('created_date', '>=', dt_from),
                ('created_date', '<=', dt_to),
            ],
            'context': {'default_site_id': site_ids[:1][0] if site_ids else False},
        }

    def action_view_active_now(self):
        self.ensure_one()
        site_ids = self._selected_site_ids()
        return {
            'name': _('En Parqueo Ahora'),
            'type': 'ir.actions.act_window',
            'res_model': 'parking.entry',
            'view_mode': 'list,form',
            'domain': [
                ('site_id', 'in', site_ids),
                ('state', '=', 'check_in'),
            ],
        }

    def action_view_pending_payments(self):
        self.ensure_one()
        dt_from = datetime.combine(self.date_from, datetime.min.time()) if self.date_from else None
        dt_to = datetime.combine(self.date_to, datetime.max.time()) if self.date_to else None
        site_ids = self._selected_site_ids()
        return {
            'name': _('Pagos Pendientes'),
            'type': 'ir.actions.act_window',
            'res_model': 'parking.entry',
            'view_mode': 'list,form',
            'domain': [
                ('site_id', 'in', site_ids),
                ('is_monthly', '=', False),
                ('created_date', '>=', dt_from),
                ('created_date', '<=', dt_to),
                ('invoice_id.state', '=', 'posted'),
                ('invoice_id.payment_state', '!=', 'paid'),
            ],
        }

    def action_view_invoices_period(self):
        self.ensure_one()
        dt_from = datetime.combine(self.date_from, datetime.min.time()) if self.date_from else None
        dt_to = datetime.combine(self.date_to, datetime.max.time()) if self.date_to else None
        site_ids = self._selected_site_ids()
        entries = self.env['parking.entry'].search([
            ('site_id', 'in', site_ids),
            ('is_monthly', '=', False),
            ('created_date', '>=', dt_from),
            ('created_date', '<=', dt_to),
            ('invoice_id', '!=', False),
        ])
        invoice_ids = entries.mapped('invoice_id').ids
        return {
            'name': _('Facturas del Periodo'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoice_ids)],
        }
