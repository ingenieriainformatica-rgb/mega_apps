# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#   This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import logging
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.tools import float_round

_logger = logging.getLogger(__name__)


class ParkingMonthlyDashboard(models.TransientModel):
    """Dashboard model for monthly parking metrics by site"""
    _name = 'parking.monthly.dashboard'
    _description = 'Parking Monthly Dashboard'

    site_id = fields.Many2one(
        'parking.site',
        string='Sitio de Parqueo',
        required=False,
        help='Sede principal (opcional si se seleccionan varias)'
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
    period_month = fields.Date(
        string='Periodo',
        required=True,
        default=fields.Date.today,
        help='Month for metrics calculation'
    )
    
    # Metrics fields
    active_contracts_count = fields.Integer(
        string='Contratos Activos',
        compute='_compute_metrics',
        help='Number of active monthly contracts for this site'
    )
    expired_contracts_count = fields.Integer(
        string='Contratos Vencidos',
        compute='_compute_metrics',
        help='Number of expired contracts for this site'
    )
    suspended_contracts_count = fields.Integer(
        string='Contratos Suspendidos',
        compute='_compute_metrics',
        help='Number of suspended contracts for this site'
    )
    recurring_revenue = fields.Monetary(
        string='Ingresos Recurrentes',
        compute='_compute_metrics',
        help='Total recurring revenue for current period'
    )
    invoiced_amount = fields.Monetary(
        string='Monto Facturado',
        compute='_compute_metrics',
        help='Total invoiced amount for current period'
    )
    entries_aggregated_count = fields.Integer(
        string='Entradas Agregadas',
        compute='_compute_metrics',
        help='Monthly entries added to invoices in current period'
    )
    entries_pending_count = fields.Integer(
        string='Entradas Pendientes',
        compute='_compute_metrics',
        help='Monthly entries pending invoice assignment in current period'
    )
    
    # Metrics by billing mode
    active_postpaid_contracts_count = fields.Integer(
        string='Contratos Postpago Activos',
        compute='_compute_metrics',
        help='Number of active postpaid contracts for this site'
    )
    active_prepaid_contracts_count = fields.Integer(
        string='Contratos Prepago Activos',
        compute='_compute_metrics',
        help='Number of active prepaid contracts for this site'
    )
    postpaid_invoiced_amount = fields.Monetary(
        string='Facturado Postpago',
        compute='_compute_metrics',
        help='Total invoiced amount for postpaid contracts'
    )
    prepaid_invoiced_amount = fields.Monetary(
        string='Facturado Prepago',
        compute='_compute_metrics',
        help='Total invoiced amount for prepaid contracts'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('site_id', 'site_ids', 'all_sites', 'period_month')
    def _compute_metrics(self):
        """Compute dashboard metrics"""
        for dashboard in self:
            site_ids = dashboard._selected_site_ids()
            if not site_ids:
                dashboard._reset_metrics()
                continue
            
            # Calculate period string
            period_string = dashboard.period_month.strftime('%Y-%m')
            
            # Active contracts
            active_contracts = self.env['parking.monthly.contract'].search([
                ('site_id', 'in', site_ids),
                ('state', '=', 'active')
            ])
            dashboard.active_contracts_count = len(active_contracts)
            
            # Active contracts by billing mode
            active_postpaid = active_contracts.filtered(lambda c: c.billing_mode == 'postpaid')
            active_prepaid = active_contracts.filtered(lambda c: c.billing_mode == 'prepaid')
            dashboard.active_postpaid_contracts_count = len(active_postpaid)
            dashboard.active_prepaid_contracts_count = len(active_prepaid)
            
            # Expired contracts
            expired_contracts = self.env['parking.monthly.contract'].search([
                ('site_id', 'in', site_ids),
                ('state', '=', 'expired')
            ])
            dashboard.expired_contracts_count = len(expired_contracts)
            
            # Suspended contracts
            suspended_contracts = self.env['parking.monthly.contract'].search([
                ('site_id', 'in', site_ids),
                ('state', '=', 'suspended')
            ])
            dashboard.suspended_contracts_count = len(suspended_contracts)
            
            # Recurring revenue (sum of active contract prices)
            dashboard.recurring_revenue = sum(active_contracts.mapped('price_unit'))
            
            # Invoiced amount for period
            monthly_invoices = self.env['account.move'].search([
                ('parking_site_id', 'in', site_ids),
                ('parking_billing_period', '=', period_string),
                ('state', '=', 'posted')
            ])
            dashboard.invoiced_amount = sum(monthly_invoices.mapped('amount_total'))
            
            # Invoiced amount by billing mode
            postpaid_invoices = monthly_invoices.filtered(lambda i: i.billing_mode == 'postpaid')
            prepaid_invoices = monthly_invoices.filtered(lambda i: i.billing_mode == 'prepaid')
            dashboard.postpaid_invoiced_amount = sum(postpaid_invoices.mapped('amount_total'))
            dashboard.prepaid_invoiced_amount = sum(prepaid_invoices.mapped('amount_total'))
            
            # Entries aggregated vs pending
            period_start = dashboard.period_month.replace(day=1)
            period_end = (period_start + relativedelta(months=1)) - relativedelta(days=1)
            
            monthly_entries = self.env['parking.entry'].search([
                ('site_id', 'in', site_ids),
                ('is_monthly', '=', True),
                ('created_date', '>=', period_start),
                ('created_date', '<=', period_end)
            ])
            
            aggregated_entries = monthly_entries.filtered(lambda e: e.monthly_invoice_id)
            pending_entries = monthly_entries.filtered(lambda e: not e.monthly_invoice_id)
            
            dashboard.entries_aggregated_count = len(aggregated_entries)
            dashboard.entries_pending_count = len(pending_entries)
            
            # Active contracts by billing mode
            active_postpaid_contracts = active_contracts.filtered(lambda c: c.billing_mode == 'postpaid')
            active_prepaid_contracts = active_contracts.filtered(lambda c: c.billing_mode == 'prepaid')
            dashboard.active_postpaid_contracts_count = len(active_postpaid_contracts)
            dashboard.active_prepaid_contracts_count = len(active_prepaid_contracts)
            
            # Invoiced amount by billing mode
            postpaid_invoices = monthly_invoices.filtered(lambda inv: inv.billing_mode == 'postpaid')
            prepaid_invoices = monthly_invoices.filtered(lambda inv: inv.billing_mode == 'prepaid')
            dashboard.postpaid_invoiced_amount = sum(postpaid_invoices.mapped('amount_total'))
            dashboard.prepaid_invoiced_amount = sum(prepaid_invoices.mapped('amount_total'))

    def _reset_metrics(self):
        """Reset all metrics to zero"""
        self.active_contracts_count = 0
        self.expired_contracts_count = 0
        self.suspended_contracts_count = 0
        self.recurring_revenue = 0
        self.invoiced_amount = 0
        self.entries_aggregated_count = 0
        self.entries_pending_count = 0
        self.active_postpaid_contracts_count = 0
        self.active_prepaid_contracts_count = 0
        self.postpaid_invoiced_amount = 0
        self.prepaid_invoiced_amount = 0
        self.active_postpaid_contracts_count = 0
        self.active_prepaid_contracts_count = 0
        self.postpaid_invoiced_amount = 0
        self.prepaid_invoiced_amount = 0

    def _selected_site_ids(self):
        """Return list of site IDs based on selection (all/sites/single)."""
        self.ensure_one()
        if self.all_sites:
            ids = self.env.user.allowed_parking_site_ids.ids
            if ids:
                return ids
            # fallback a todas si no hay restricción específica
            return self.env['parking.site'].search([]).ids
        if self.site_ids:
            return self.site_ids.ids
        if self.site_id:
            return [self.site_id.id]
        return []

    @api.model
    def get_site_domain(self):
        """Get domain for sites accessible by current user"""
        return self.env.user.get_user_parking_sites_domain()

    @api.model
    def default_get(self, fields_list):
        """Set default site based on user"""
        defaults = super().default_get(fields_list)
        
        if 'site_id' in fields_list and not defaults.get('site_id'):
            default_site = self.env.user.get_default_parking_site()
            if default_site:
                defaults['site_id'] = default_site.id
        
        return defaults

    def action_view_active_contracts(self):
        """View active contracts for this site"""
        site_ids = self._selected_site_ids()
        return {
            'name': _('Contratos Activos'),
            'type': 'ir.actions.act_window',
            'res_model': 'parking.monthly.contract',
            'view_mode': 'list,form',
            'domain': [
                ('site_id', 'in', site_ids),
                ('state', '=', 'active')
            ],
            'context': {'default_site_id': site_ids[:1][0] if site_ids else False},
        }

    def action_view_expired_contracts(self):
        """View expired contracts for this site"""
        site_ids = self._selected_site_ids()
        return {
            'name': _('Contratos Vencidos'),
            'type': 'ir.actions.act_window',
            'res_model': 'parking.monthly.contract',
            'view_mode': 'list,form',
            'domain': [
                ('site_id', 'in', site_ids),
                ('state', '=', 'expired')
            ],
        }

    def action_view_monthly_invoices(self):
        """View monthly invoices for current period"""
        period_string = self.period_month.strftime('%Y-%m')
        site_ids = self._selected_site_ids()
        return {
            'name': _('Facturas de Mensualidades'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('parking_site_id', 'in', site_ids),
                ('parking_billing_period', '=', period_string)
            ],
        }

    def action_view_pending_entries(self):
        """View pending monthly entries"""
        period_start = self.period_month.replace(day=1)
        period_end = (period_start + relativedelta(months=1)) - relativedelta(days=1)
        site_ids = self._selected_site_ids()
        return {
            'name': _('Entradas Pendientes'),
            'type': 'ir.actions.act_window',
            'res_model': 'parking.entry',
            'view_mode': 'list,form',
            'domain': [
                ('site_id', 'in', site_ids),
                ('is_monthly', '=', True),
                ('monthly_invoice_id', '=', False),
                ('created_date', '>=', period_start),
                ('created_date', '<=', period_end)
            ],
        }

    def action_publish_draft_invoices(self):
        """Publicar facturas mensuales en borrador para las sedes seleccionadas"""
        period_string = self.period_month.strftime('%Y-%m')
        site_ids = self._selected_site_ids()

        published_count = 0
        for sid in site_ids:
            draft_invoices = self.env['account.move'].search([
                ('parking_site_id', '=', sid),
                ('parking_billing_period', '=', period_string),
                ('state', '=', 'draft')
            ])
            for invoice in draft_invoices:
                try:
                    invoice.action_post()
                    published_count += 1
                except Exception as e:
                    _logger.error(f"Error publishing invoice {invoice.name}: {e}")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Se publicaron %d facturas') % published_count,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_process_pending_entries(self):
        """Procesar entradas pendientes para las sedes seleccionadas"""
        monthly_service = self.env['parking.monthly.service']

        period_start = self.period_month.replace(day=1)
        period_end = (period_start + relativedelta(months=1)) - relativedelta(days=1)

        processed_count = 0
        for sid in self._selected_site_ids():
            pending_entries = self.env['parking.entry'].search([
                ('site_id', '=', sid),
                ('is_monthly', '=', True),
                ('monthly_invoice_id', '=', False),
                ('created_date', '>=', period_start),
                ('created_date', '<=', period_end),
                ('state', 'in', ('check_out', 'payment'))
            ])
            for entry in pending_entries:
                try:
                    monthly_service.add_entry_to_monthly_invoice(entry)
                    processed_count += 1
                except Exception as e:
                    _logger.error(f"Error processing entry {entry.name}: {e}")

        # Refresh computed fields
        self._compute_metrics()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Se procesaron %d entradas pendientes') % processed_count,
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def get_dashboard_data(self, site_id, period_month=None):
        """Get dashboard data for API/JS calls"""
        if not period_month:
            period_month = date.today()
        elif isinstance(period_month, str):
            period_month = datetime.strptime(period_month, '%Y-%m-%d').date()
        
        dashboard = self.create({
            'site_id': site_id,
            'period_month': period_month
        })
        
        return {
            'site_id': dashboard.site_id.id,
            'site_name': dashboard.site_id.name,
            'period_month': dashboard.period_month.strftime('%Y-%m'),
            'active_contracts_count': dashboard.active_contracts_count,
            'expired_contracts_count': dashboard.expired_contracts_count,
            'suspended_contracts_count': dashboard.suspended_contracts_count,
            'recurring_revenue': dashboard.recurring_revenue,
            'invoiced_amount': dashboard.invoiced_amount,
            'entries_aggregated_count': dashboard.entries_aggregated_count,
            'entries_pending_count': dashboard.entries_pending_count,
            'currency_symbol': dashboard.currency_id.symbol,
        }

    def action_view_postpaid_contracts(self):
        """View active postpaid contracts for this site"""
        site_ids = self._selected_site_ids()
        return {
            'name': _('Contratos Postpago Activos'),
            'type': 'ir.actions.act_window',
            'res_model': 'parking.monthly.contract',
            'view_mode': 'list,form',
            'domain': [
                ('site_id', 'in', site_ids),
                ('state', '=', 'active'),
                ('billing_mode', '=', 'postpaid')
            ],
            'context': {'default_site_id': site_ids[:1][0] if site_ids else False, 'default_billing_mode': 'postpaid'},
        }

    def action_view_prepaid_contracts(self):
        """View active prepaid contracts for this site"""
        site_ids = self._selected_site_ids()
        return {
            'name': _('Contratos Prepago Activos'),
            'type': 'ir.actions.act_window',
            'res_model': 'parking.monthly.contract',
            'view_mode': 'list,form',
            'domain': [
                ('site_id', 'in', site_ids),
                ('state', '=', 'active'),
                ('billing_mode', '=', 'prepaid')
            ],
            'context': {'default_site_id': site_ids[:1][0] if site_ids else False, 'default_billing_mode': 'prepaid'},
        }
