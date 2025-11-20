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
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class ParkingMonthlyContract(models.Model):
    """Monthly contracts for regular parking customers"""
    _name = 'parking.monthly.contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Personal Autorizado'
    _order = 'partner_id, site_id, start_date desc'

    name = fields.Char(
        string='Contract Name',
        required=True,
        tracking=True,
        help='Label for this monthly contract'
    )
    # Capacity (Cupos Adquiridos)
    acquired_slots = fields.Integer(
        string='Cupos Adquiridos',
        default=1,
        required=True,
        tracking=True,
        help='Número de vehículos permitidos simultáneamente dentro del parqueadero para este contrato.'
    )
    # Authorized plates per contract
    authorized_vehicle_ids = fields.One2many(
        'parking.authorized.vehicle',
        'contract_id',
        string='Placas Autorizadas',
        help='Lista de placas autorizadas para este personal autorizado.'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        help='Customer for this monthly contract'
    )
    site_id = fields.Many2one(
        'parking.site',
        string='Parking Site',
        required=True,
        tracking=True,
        index=True,
        help='Parking site for this contract'
    )
    plan_product_id = fields.Many2one(
        'product.product',
        string='Monthly Plan Product',
        required=True,
        domain=[('type', '=', 'service'), ('sale_ok', '=', True)],
        tracking=True,
        help='Service product for monthly parking plan'
    )
    price_unit = fields.Monetary(
        string='Monthly Price',
        required=True,
        tracking=True,
        help='Monthly plan price (overrides product price if set)'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency for this contract'
    )
    # Deprecated: monthly contracts are now fixed to 1 month from start_date
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
        help='Contract start date'
    )
    end_date = fields.Date(
        string='End Date',
        compute='_compute_end_date',
        store=True,
        tracking=True,
        help='Contract end date (auto = start date + 1 month)'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired')
    ], string='Status', default='draft', tracking=True, help='Contract status')
    
    # Billing mode field
    billing_mode = fields.Selection([
        ('prepaid', 'Mes Anticipado')
    ], string='Billing Mode', default='prepaid', required=True, tracking=True,
       help='Postpaid: consolidates all tickets in monthly invoice\n'
            'Prepaid: creates single advance invoice for monthly plan')
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help='Company for this contract'
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        help='Analytic account for tracking by site'
    )
    
    # Computed fields
    is_expired = fields.Boolean(
        string='Is Expired',
        compute='_compute_is_expired',
        store=True,
        help='True if contract has expired'
    )
    current_period = fields.Char(
        string='Current Period',
        compute='_compute_current_period',
        help='Current billing period (YYYY-MM)'
    )
    
    # Stats fields
    total_entries_count = fields.Integer(
        string='Total Entries',
        compute='_compute_entry_stats',
        help='Total parking entries for this contract'
    )
    current_month_entries_count = fields.Integer(
        string='Current Month Entries',
        compute='_compute_entry_stats',
        help='Parking entries for current month'
    )
    total_invoiced_amount = fields.Monetary(
        string='Total Invoiced',
        compute='_compute_invoice_stats',
        help='Total amount invoiced for this contract'
    )
    unpaid_invoices_count = fields.Integer(
        string='Unpaid Invoices',
        compute='_compute_unpaid_invoices_count',
        help='Number of unpaid customer invoices for this customer'
    )

    @api.depends('start_date')
    def _compute_end_date(self):
        for contract in self:
            contract.end_date = (contract.start_date + relativedelta(months=1)) if contract.start_date else False

    # --------------------------------------------------------------
    # Product helpers
    # --------------------------------------------------------------
    @api.model
    def _ensure_plan_product(self):
        """Ensure the default monthly plan product exists and return it.

        Product: 'Mensualidad Personal Autorizado' (service, sale_ok)
        """
        name = 'Mensualidad Personal Autorizado'
        Product = self.env['product.product']
        prod = Product.search([('name', '=', name), ('type', '=', 'service')], limit=1)
        if prod:
            return prod
        # Create product template via product.product
        prod = Product.create({
            'name': name,
            'type': 'service',
            'sale_ok': True,
        })
        return prod

    @api.depends('end_date')
    def _compute_is_expired(self):
        """Compute if contract is expired"""
        today = fields.Date.today()
        for contract in self:
            contract.is_expired = contract.end_date and contract.end_date < today

    def _compute_current_period(self):
        """Set current period label based on start date month.

        Contracts are month-to-month from start_date to start_date + 1 month.
        """
        for contract in self:
            if contract.start_date:
                contract.current_period = contract.start_date.strftime('%Y-%m')
            else:
                contract.current_period = False

    def _compute_entry_stats(self):
        """Compute parking entry statistics"""
        for contract in self:
            entries = self.env['parking.entry'].search([
                ('monthly_contract_id', '=', contract.id)
            ])
            contract.total_entries_count = len(entries)
            
            # Current month entries
            current_period = contract.current_period
            if current_period:
                year, month = current_period.split('-')
                current_entries = entries.filtered(
                    lambda e: e.monthly_period == current_period
                )
                contract.current_month_entries_count = len(current_entries)
            else:
                contract.current_month_entries_count = 0

    def _compute_invoice_stats(self):
        """Compute invoice statistics"""
        for contract in self:
            invoices = self.env['account.move'].search([
                ('monthly_contract_id', '=', contract.id),
                ('state', '=', 'posted')
            ])
            contract.total_invoiced_amount = sum(invoices.mapped('amount_total'))

    def _compute_unpaid_invoices_count(self):
        """Compute how many unpaid invoices the contract's customer has"""
        Move = self.env['account.move']
        for contract in self:
            if not contract.partner_id:
                contract.unpaid_invoices_count = 0
                continue
            domain = [
                ('partner_id', '=', contract.partner_id.id),
                ('company_id', '=', contract.company_id.id),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted'),
                ('payment_state', '!=', 'paid'),
            ]
            contract.unpaid_invoices_count = Move.search_count(domain)

    def action_view_unpaid_invoices(self):
        """Open customer invoices in unpaid state for this contract's customer"""
        self.ensure_one()
        domain = [
            ('partner_id', '=', self.partner_id.id),
            ('company_id', '=', self.company_id.id),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('payment_state', '!=', 'paid'),
        ]
        return {
            'name': _('Facturas sin pagar'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
        }

    @api.constrains('partner_id', 'site_id', 'state', 'start_date', 'end_date')
    def _check_unique_active_contract(self):
        """Ensure only one active contract per partner+site"""
        for contract in self:
            if contract.state in ('active', 'suspended'):
                overlapping = self.search([
                    ('partner_id', '=', contract.partner_id.id),
                    ('site_id', '=', contract.site_id.id),
                    ('state', 'in', ('active', 'suspended')),
                    ('id', '!=', contract.id)
                ])
                
                for other in overlapping:
                    # Check date overlap
                    if self._dates_overlap(contract, other):
                        raise ValidationError(_(
                            'Customer "%s" already has an active/suspended contract '
                            'for site "%s" with overlapping dates.'
                        ) % (contract.partner_id.name, contract.site_id.name))

    def _dates_overlap(self, contract1, contract2):
        """Check if two contracts have overlapping date ranges"""
        # If either has no end date, they overlap if start dates are valid
        if not contract1.end_date or not contract2.end_date:
            return True
        
        # Check for date range overlap
        return (contract1.start_date <= contract2.end_date and 
                contract2.start_date <= contract1.end_date)

    @api.constrains('site_id')
    def _check_site_access(self):
        """Validate that user has access to the selected site"""
        for contract in self:
            if contract.site_id:
                user = self.env.user
                # Skip validation for admins
                if user.has_group('odoo_parking_management.group_parking_admin'):
                    continue
                # Check if user has access to this site
                if contract.site_id not in user.allowed_parking_site_ids:
                    raise ValidationError(_(
                        'You do not have access to site "%s". Please contact your administrator.'
                    ) % contract.site_id.name)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Validate contract dates"""
        for contract in self:
            if contract.end_date and contract.start_date > contract.end_date:
                raise ValidationError(_('End date must be after start date.'))

    @api.constrains('price_unit', 'state')
    def _check_price_unit(self):
        """Validate price unit is positive for active contracts"""
        for contract in self:
            # Only check positive price for active contracts
            if contract.state == 'active' and contract.price_unit <= 0:
                raise ValidationError(_('Monthly price must be positive for active contracts.'))

    @api.onchange('plan_product_id')
    def _onchange_plan_product_id(self):
        """Auto-fill price from product"""
        if self.plan_product_id:
            self.price_unit = self.plan_product_id.list_price

    @api.onchange('partner_id', 'site_id')
    def _onchange_partner_site(self):
        """Auto-generate contract name"""
        if self.partner_id and self.site_id:
            self.name = _('Personal Autorizado - %s - %s') % (self.partner_id.name, self.site_id.name)

    @api.onchange('site_id')
    def _onchange_site_id(self):
        """Auto-set analytic account from site"""
        if self.site_id and self.site_id.analytic_account_id:
            self.analytic_account_id = self.site_id.analytic_account_id

    @api.model
    def get_site_domain(self):
        """Get domain for sites accessible by current user"""
        return self.env.user.get_user_parking_sites_domain()

    @api.model
    def default_get(self, fields_list):
        """Set default values"""
        defaults = super().default_get(fields_list)
        
        # Set default site_id based on user configuration
        if 'site_id' in fields_list and not defaults.get('site_id'):
            default_site = self.env.user.get_default_parking_site()
            if default_site:
                defaults['site_id'] = default_site.id
        
        # Set default start_date to today
        if 'start_date' in fields_list and not defaults.get('start_date'):
            defaults['start_date'] = fields.Date.today()
        
        # end_date is computed from start_date; no default needed
        
        # Force default billing_mode to prepaid
        if 'billing_mode' in fields_list and not defaults.get('billing_mode'):
            defaults['billing_mode'] = 'prepaid'

        # Default plan product: always 'Mensualidad Personal Autorizado'
        if 'plan_product_id' in fields_list and not defaults.get('plan_product_id'):
            prod = self._ensure_plan_product()
            if prod:
                defaults['plan_product_id'] = prod.id

        return defaults

    def action_activate(self):
        """Activate the contract"""
        for contract in self.with_context(allow_immutable=True):
            if contract.state != 'draft':
                raise UserError(_('Only draft contracts can be activated.'))
            
            # Basic validation (fields are already required at model level)
            if contract.price_unit <= 0:
                raise UserError(_('Monthly price must be positive.'))
            
            # Ensure fixed plan product
            product = contract.plan_product_id or contract._ensure_plan_product()
            if not contract.plan_product_id:
                contract.plan_product_id = product.id

            # Activate
            contract.state = 'active'

            # Create initial invoice (prepaid first month)
            try:
                invoice = contract._create_activation_invoice()
                if invoice and invoice.state == 'draft':
                    invoice.action_post()
            except Exception as e:
                _logger.error(f"Error creating activation invoice for contract {contract.name}: {e}")
                # Do not rollback activation due to invoicing issues
                pass

    def action_renew(self):
        """Create a new 1-month contract starting the day after this one ends.

        Opens a prefilled form in edit mode.
        """
        self.ensure_one()
        next_start = (self.end_date or fields.Date.today())
        ctx = {
            'default_partner_id': self.partner_id.id,
            'default_site_id': self.site_id.id,
            'default_plan_product_id': self.plan_product_id.id,
            'default_price_unit': self.price_unit,
            'default_start_date': next_start,
            'form_view_initial_mode': 'edit',
            'default_state': 'draft',
        }
        return {
            'name': _('Renovar Personal Autorizado'),
            'type': 'ir.actions.act_window',
            'res_model': 'parking.monthly.contract',
            'view_mode': 'form',
            'view_id': self.env.ref('odoo_parking_management.parking_monthly_contract_view_form').id,
            'target': 'current',
            'context': ctx,
        }

    def action_suspend(self):
        """Suspender contrato: deshabilitado.

        Esta acción ya no está permitida por política. Se mantiene el método
        para compatibilidad, pero siempre genera un error.
        """
        raise UserError(_('La opción de suspender contratos está deshabilitada.'))

    def action_reactivate(self):
        """Reactivate suspended contract"""
        for contract in self.with_context(allow_immutable=True):
            if contract.state != 'suspended':
                raise UserError(_('Only suspended contracts can be reactivated.'))
            contract.state = 'active'

    def action_expire(self):
        """Expire the contract"""
        for contract in self.with_context(allow_immutable=True):
            if contract.state not in ('active', 'suspended'):
                raise UserError(_('Only active or suspended contracts can be expired.'))
            contract.state = 'expired'

    def action_view_entries(self):
        """View parking entries for this contract"""
        return {
            'name': _('Parking Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'parking.entry',
            'view_mode': 'list,form',
            'domain': [('monthly_contract_id', '=', self.id)],
            'context': {'default_monthly_contract_id': self.id},
        }

    def action_view_invoices(self):
        """View monthly invoices for this contract"""
        return {
            'name': _('Monthly Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('monthly_contract_id', '=', self.id)],
        }

    @api.model
    def _cron_expire_contracts(self):
        """Cron job to expire contracts automatically"""
        today = fields.Date.today()
        expired_contracts = self.search([
            ('state', 'in', ('active', 'suspended')),
            ('end_date', '<', today)
        ])

        for contract in expired_contracts.with_context(allow_immutable=True):
            contract.state = 'expired'
            _logger.info(f"Auto-expired contract {contract.name} (ID: {contract.id})")

    def write(self, vals):
        """Make contracts immutable after leaving draft, except for system actions.

        Allows only controlled updates in non-draft: state transitions and
        technical chatter/activity fields. Use context key `allow_immutable`
        for internal system flows when needed.
        """
        if vals and not self.env.context.get('allow_immutable'):
            allowed_fields = {'state', 'is_expired'}
            def _is_technical_field(fname):
                return fname.startswith('message_') or fname.startswith('activity_')

            non_draft = self.filtered(lambda r: r.state != 'draft')
            if non_draft:
                disallowed = {f for f in vals.keys() if f not in allowed_fields and not _is_technical_field(f)}
                if disallowed:
                    raise UserError(_(
                        'La Mensualidad es de solo lectura después de salir de Borrador. No puede modificar los siguientes campos: %s'
                    ) % ', '.join(sorted(disallowed)))

        return super().write(vals)

    def unlink(self):
        """Prevent deleting contracts that are not in draft."""
        non_draft = self.filtered(lambda r: r.state != 'draft')
        if non_draft and not self.env.context.get('allow_immutable'):
            raise UserError(_('You can only delete monthly contracts in Draft state.'))
        return super().unlink()

    def get_period_key(self, period_date=None):
        """Get unique period key for this contract"""
        # Period identified by the start_date month of the contract
        base = self.start_date or fields.Date.today()
        return (
            self.id,
            self.site_id.id,
            self.partner_id.id,
            self.company_id.id,
            base.year,
            base.month
        )

    def get_period_string(self, period_date=None):
        """Get period string (YYYY-MM) for this contract"""
        period_key = self.get_period_key(period_date)
        return f"{period_key[4]:04d}-{period_key[5]:02d}"

    @api.model
    def find_active_contract(self, partner_id, site_id, entry_date=None):
        """Find active contract for partner+site on given date"""
        if not entry_date:
            entry_date = fields.Date.today()
        
        contracts = self.search([
            ('partner_id', '=', partner_id),
            ('site_id', '=', site_id),
            ('state', 'in', ('active', 'suspended')),
            ('start_date', '<=', entry_date),
            '|',
            ('end_date', '=', False),
            ('end_date', '>=', entry_date)
        ])
        
        return contracts[0] if contracts else False

    # --------------------------------------------------------------
    # Access control helpers for authorized plates and capacity
    # --------------------------------------------------------------
    @api.model
    def _normalize_plate(self, plate):
        """Normalize a plate string for consistent comparisons."""
        if not plate:
            return False
        return ''.join(str(plate).upper().strip().split())

    @api.model
    def find_contract_by_plate(self, site_id, plate, entry_date=None):
        """Find an active/suspended contract by authorized plate and site.

        Returns the matching contract record or False.
        """
        if not plate or not site_id:
            return False
        norm = self._normalize_plate(plate)
        if not entry_date:
            entry_date = fields.Date.today()

        # Find authorized vehicle lines first for quick match
        auth_lines = self.env['parking.authorized.vehicle'].search([
            ('vehicle_number_normalized', '=', norm),
            ('contract_id.site_id', '=', site_id),
            ('contract_id.state', 'in', ('active', 'suspended')),
        ])
        if not auth_lines:
            return False

        # Filter by date window
        def _date_ok(c):
            if c.start_date and c.start_date > entry_date:
                return False
            if c.end_date and c.end_date < entry_date:
                return False
            return True

        for line in auth_lines:
            c = line.contract_id
            if _date_ok(c):
                return c
        return False

    def get_current_inside_count(self):
        """Count vehicles currently inside for this contract (state=check_in)."""
        self.ensure_one()
        return self.env['parking.entry'].search_count([
            ('monthly_contract_id', '=', self.id),
            ('state', '=', 'check_in')
        ])

    def _create_activation_invoice(self):
        """Create the initial invoice for the first month upon activation."""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('Customer is required.'))
        if not self.plan_product_id:
            self.plan_product_id = self._ensure_plan_product().id
        if self.price_unit <= 0:
            raise UserError(_('Monthly price must be positive.'))

        # Obtain journal from service helper
        journal = self.env['parking.monthly.service']._get_parking_journal(self.company_id)
        period_string = self.get_period_string(self.start_date or fields.Date.today())
        period_key = self.get_period_key(self.start_date or fields.Date.today())
        parking_period_key = f"{period_key[0]}-{period_key[1]}-{period_key[2]}-{period_key[3]}-{period_key[4]}-{period_key[5]}"

        analytic_distribution = {}
        if self.site_id and self.site_id.analytic_account_id:
            analytic_distribution = {str(self.site_id.analytic_account_id.id): 100.0}

        line_vals = {
            'product_id': self.plan_product_id.id,
            'name': f'{self.plan_product_id.name} - {self.name} - {period_string}',
            'quantity': 1,
            'price_unit': self.price_unit,
            'product_uom_id': self.plan_product_id.uom_id.id,
        }
        if analytic_distribution:
            line_vals['analytic_distribution'] = analytic_distribution

        move_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'journal_id': journal.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_origin': f'Mensualidad - {period_string}',
            'ref': f'{self.name} - {period_string}',
            'company_id': self.company_id.id,
            'monthly_contract_id': self.id,
            'parking_period_key': parking_period_key,
            'parking_billing_period': period_string,
            'parking_site_id': self.site_id.id,
            'invoice_line_ids': [(0, 0, line_vals)],
        }
        if self.partner_id.property_payment_term_id:
            move_vals['invoice_payment_term_id'] = self.partner_id.property_payment_term_id.id

        invoice = self.env['account.move'].create(move_vals)
        return invoice

    def action_save(self):
        """Explicit save button: the client will save changes before calling.

        Shows a small notification to confirm the save.
        """
        self.ensure_one()
        return { 
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Guardado'),
                'message': _('El contrato se ha guardado.'),
                'sticky': False,
                'type': 'success',
            }
        }
