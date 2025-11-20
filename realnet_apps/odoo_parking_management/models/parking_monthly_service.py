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
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ParkingMonthlyService(models.TransientModel):
    """Service for managing monthly parking invoices and aggregation"""
    _name = 'parking.monthly.service'
    _description = 'Parking Monthly Aggregation Service'

    @api.model
    def _get_or_create_monthly_invoice(self, contract, period_date=None):
        """Get or create monthly invoice for contract and period"""
        if not period_date:
            period_date = date.today()
        
        # Calculate period key and string
        period_key = contract.get_period_key(period_date)
        period_string = contract.get_period_string(period_date)
        
        # Create unique key for constraint
        parking_period_key = f"{period_key[0]}-{period_key[1]}-{period_key[2]}-{period_key[3]}-{period_key[4]}-{period_key[5]}"
        
        # Search for existing invoice - include billing_mode for uniqueness
        existing_invoice = self.env['account.move'].search([
            ('monthly_contract_id', '=', contract.id),
            ('parking_site_id', '=', contract.site_id.id),
            ('partner_id', '=', contract.partner_id.id),
            ('parking_billing_period', '=', period_string),
            ('billing_mode', '=', contract.billing_mode),
            ('state', '!=', 'cancel')
        ], limit=1)
        
        if existing_invoice:
            return existing_invoice
        
        # Get journal for parking invoices
        journal = self._get_parking_journal(contract.company_id)
        
        # Prepare analytic distribution
        analytic_distribution = {}
        if contract.analytic_account_id:
            analytic_distribution = {str(contract.analytic_account_id.id): 100.0}
        elif contract.site_id.analytic_account_id:
            analytic_distribution = {str(contract.site_id.analytic_account_id.id): 100.0}
        
        # Create base invoice line for monthly plan
        base_line_vals = {
            'product_id': contract.plan_product_id.id,
            'name': f'{contract.plan_product_id.name} - {contract.name} - {period_string}',
            'quantity': 1,
            'price_unit': contract.price_unit,
            'product_uom_id': contract.plan_product_id.uom_id.id,
        }
        
        if analytic_distribution:
            base_line_vals['analytic_distribution'] = analytic_distribution
        
        # Create invoice
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': contract.partner_id.id,
            'journal_id': journal.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_origin': f'Monthly Parking - {period_string}',
            'ref': f'{contract.name} - {period_string}',
            'company_id': contract.company_id.id,
            'monthly_contract_id': contract.id,
            'parking_period_key': parking_period_key,
            'parking_billing_period': period_string,
            'parking_site_id': contract.site_id.id,
            'invoice_line_ids': [(0, 0, base_line_vals)],
        }
        
        # Set payment terms if available
        if contract.partner_id.property_payment_term_id:
            invoice_vals['invoice_payment_term_id'] = contract.partner_id.property_payment_term_id.id
        
        invoice = self.env['account.move'].create(invoice_vals)
        
        _logger.info(f"Created monthly invoice {invoice.name} for contract {contract.name} period {period_string}")
        
        return invoice

    @api.model
    def _get_parking_journal(self, company):
        """Get parking journal for invoices"""
        # First try to find specific parking journal
        journal = self.env['account.journal'].search([
            ('name', '=', 'Facturas de parqueadero'),
            ('type', '=', 'sale'),
            ('company_id', '=', company.id)
        ], limit=1)
        
        # Fallback to any sale journal
        if not journal:
            journal = self.env['account.journal'].search([
                ('type', '=', 'sale'),
                ('company_id', '=', company.id)
            ], limit=1)
        
        if not journal:
            raise UserError(_('No sale journal found for company %s') % company.name)
        
        return journal

    @api.model
    def add_entry_to_monthly_invoice(self, parking_entry):
        """Add parking entry to its monthly invoice (postpaid only)"""
        if not parking_entry.is_monthly or not parking_entry.monthly_contract_id:
            return False
        
        # For prepaid contracts, tickets are not added to invoices
        if parking_entry.monthly_contract_id.billing_mode == 'prepaid':
            _logger.debug(f"Skipping ticket aggregation for prepaid contract: {parking_entry.name}")
            return False
        
        if parking_entry.monthly_invoice_id:
            # Already added
            return parking_entry.monthly_invoice_id
        
        # Get or create monthly invoice for postpaid contracts
        invoice = self._get_or_create_monthly_invoice(
            parking_entry.monthly_contract_id,
            parking_entry.created_date.date() if parking_entry.created_date else date.today()
        )
        
        # Check if invoice is in draft state
        if invoice.state != 'draft':
            _logger.warning(f"Cannot add entry {parking_entry.name} to posted invoice {invoice.name}")
            return invoice
        
        # Prepare analytic distribution
        analytic_distribution = {}
        if parking_entry.monthly_contract_id.analytic_account_id:
            analytic_distribution = {str(parking_entry.monthly_contract_id.analytic_account_id.id): 100.0}
        elif parking_entry.site_id.analytic_account_id:
            analytic_distribution = {str(parking_entry.site_id.analytic_account_id.id): 100.0}
        
        # Create invoice line for this entry
        entry_line_vals = {
            'move_id': invoice.id,
            'product_id': parking_entry.product_id.id if parking_entry.product_id else parking_entry.monthly_contract_id.plan_product_id.id,
            'name': f'[{parking_entry.receipt_sequence}] {parking_entry.slot_type_id.vehicle_type if parking_entry.slot_type_id else "Parking"} - {parking_entry.created_date.strftime("%Y-%m-%d %H:%M") if parking_entry.created_date else ""}',
            'quantity': max(1, parking_entry.duration) if parking_entry.duration else 1,
            'price_unit': 0,  # Include in monthly plan, no additional charge
            'product_uom_id': parking_entry.product_id.uom_id.id if parking_entry.product_id else parking_entry.monthly_contract_id.plan_product_id.uom_id.id,
        }
        
        if analytic_distribution:
            entry_line_vals['analytic_distribution'] = analytic_distribution
        
        # Create the line
        line = self.env['account.move.line'].create(entry_line_vals)
        
        # Link entry to invoice
        parking_entry.monthly_invoice_id = invoice.id
        
        _logger.info(f"Added entry {parking_entry.name} to monthly invoice {invoice.name}")
        
        return invoice

    @api.model
    def process_pending_monthly_entries(self):
        """Process parking entries that need to be added to monthly invoices"""
        # Find monthly entries without invoice assignment
        pending_entries = self.env['parking.entry'].search([
            ('is_monthly', '=', True),
            ('monthly_contract_id', '!=', False),
            ('monthly_invoice_id', '=', False),
            ('state', 'in', ('check_out', 'payment'))
        ])
        
        processed_count = 0
        for entry in pending_entries:
            try:
                self.add_entry_to_monthly_invoice(entry)
                processed_count += 1
            except Exception as e:
                _logger.error(f"Error processing entry {entry.name}: {e}")
        
        _logger.info(f"Processed {processed_count} pending monthly entries")
        return processed_count

    @api.model
    def publish_monthly_invoices(self, site_ids=None, contract_ids=None):
        """Publish monthly invoices on contract end date (month-to-month)."""
        today = date.today()
        
        # Build domain for contracts that end today
        domain = [
            ('state', '=', 'active'),
            ('end_date', '=', today)
        ]
        
        if site_ids:
            domain.append(('site_id', 'in', site_ids))
        if contract_ids:
            domain.append(('id', 'in', contract_ids))
        
        contracts = self.env['parking.monthly.contract'].search(domain)
        
        published_count = 0
        for contract in contracts:
            try:
                # Get current period invoice
                period_string = contract.get_period_string(today)
                invoice = self.env['account.move'].search([
                    ('monthly_contract_id', '=', contract.id),
                    ('parking_billing_period', '=', period_string),
                    ('state', '=', 'draft')
                ], limit=1)
                
                if invoice:
                    invoice.action_post()
                    published_count += 1
                    _logger.info(f"Published monthly invoice {invoice.name} for contract {contract.name}")
                
            except Exception as e:
                _logger.error(f"Error publishing invoice for contract {contract.name}: {e}")
        
        _logger.info(f"Published {published_count} monthly invoices")
        return published_count

    @api.model
    def generate_prepaid_invoices(self, site_ids=None, contract_ids=None):
        """Generate prepaid invoices for contracts on their end date."""
        today = date.today()
        
        # Build domain for prepaid contracts that end today
        domain = [
            ('state', '=', 'active'),
            ('billing_mode', '=', 'prepaid'),
            ('end_date', '=', today)
        ]
        
        if site_ids:
            domain.append(('site_id', 'in', site_ids))
        if contract_ids:
            domain.append(('id', 'in', contract_ids))
        
        contracts = self.env['parking.monthly.contract'].search(domain)
        
        generated_count = 0
        for contract in contracts:
            try:
                # Generate advance invoice for next period
                next_period_date = today + relativedelta(months=1)
                invoice = self._create_prepaid_invoice(contract, next_period_date)
                
                if invoice:
                    generated_count += 1
                    _logger.info(f"Generated prepaid invoice {invoice.name} for contract {contract.name}")
                
            except Exception as e:
                _logger.error(f"Error generating prepaid invoice for contract {contract.name}: {e}")
        
        _logger.info(f"Generated {generated_count} prepaid invoices")
        return generated_count

    @api.model
    def _cron_process_monthly_entries(self):
        """Cron job to process pending monthly entries"""
        return self.process_pending_monthly_entries()

    @api.model
    def _cron_publish_monthly_invoices(self):
        """Cron job to publish monthly invoices and generate prepaid invoices on billing day"""
        # Process postpaid invoices (publish existing draft invoices)
        published_count = self.publish_monthly_invoices()
        
        # Generate new prepaid invoices for next period
        generated_count = self.generate_prepaid_invoices()
        
        _logger.info(f"CRON completed: {published_count} postpaid invoices published, {generated_count} prepaid invoices generated")
        return published_count + generated_count

    @api.model
    def backfill_historical_entries(self, limit_months=12):
        """Backfill historical monthly entries to invoices"""
        _logger.info("Starting backfill of historical monthly entries")
        
        # Get date range for backfill
        end_date = date.today()
        start_date = end_date - relativedelta(months=limit_months)
        
        # Find monthly entries without invoice assignment in the period
        historical_entries = self.env['parking.entry'].search([
            ('is_monthly', '=', True),
            ('monthly_contract_id', '!=', False),
            ('monthly_invoice_id', '=', False),
            ('created_date', '>=', start_date),
            ('created_date', '<=', end_date)
        ])
        
        processed_count = 0
        for entry in historical_entries:
            try:
                self.add_entry_to_monthly_invoice(entry)
                processed_count += 1
            except Exception as e:
                _logger.error(f"Error backfilling entry {entry.name}: {e}")
        
        _logger.info(f"Backfilled {processed_count} historical entries")
        return processed_count

    @api.model
    def _create_prepaid_invoice(self, contract, period_date=None):
        """Create prepaid invoice for contract (advance payment)"""
        if not period_date:
            period_date = date.today()
        
        # For prepaid, we create invoice for current period
        period_key = contract.get_period_key(period_date)
        period_string = contract.get_period_string(period_date)
        
        # Create unique key for constraint
        parking_period_key = f"{period_key[0]}-{period_key[1]}-{period_key[2]}-{period_key[3]}-{period_key[4]}-{period_key[5]}"
        
        # Check if prepaid invoice already exists for this period
        existing_invoice = self.env['account.move'].search([
            ('monthly_contract_id', '=', contract.id),
            ('parking_site_id', '=', contract.site_id.id),
            ('partner_id', '=', contract.partner_id.id),
            ('parking_billing_period', '=', period_string),
            ('billing_mode', '=', 'prepaid'),
            ('state', '!=', 'cancel')
        ], limit=1)
        
        if existing_invoice:
            _logger.info(f"Prepaid invoice already exists for contract {contract.name} period {period_string}: {existing_invoice.name}")
            return existing_invoice
        
        # Get journal for parking invoices
        journal = self._get_parking_journal(contract.company_id)
        
        # Prepare analytic distribution
        analytic_distribution = {}
        if contract.analytic_account_id:
            analytic_distribution = {str(contract.analytic_account_id.id): 100.0}
        elif contract.site_id.analytic_account_id:
            analytic_distribution = {str(contract.site_id.analytic_account_id.id): 100.0}
        
        # Create single invoice line for prepaid plan (no tickets included)
        prepaid_line_vals = {
            'product_id': contract.plan_product_id.id,
            'name': f'Mensualidad Parking {period_string} (Prepago) - {contract.plan_product_id.name}',
            'quantity': 1,
            'price_unit': contract.price_unit,
            'product_uom_id': contract.plan_product_id.uom_id.id,
        }
        
        if analytic_distribution:
            prepaid_line_vals['analytic_distribution'] = analytic_distribution
        
        # Create prepaid invoice
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': contract.partner_id.id,
            'journal_id': journal.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_origin': f'Monthly Parking Prepaid - {period_string}',
            'ref': f'{contract.name} - {period_string} (Prepago)',
            'company_id': contract.company_id.id,
            'monthly_contract_id': contract.id,
            'parking_period_key': parking_period_key,
            'parking_billing_period': period_string,
            'parking_site_id': contract.site_id.id,
            'invoice_line_ids': [(0, 0, prepaid_line_vals)],
        }
        
        # Set payment terms if available
        if contract.partner_id.property_payment_term_id:
            invoice_vals['invoice_payment_term_id'] = contract.partner_id.property_payment_term_id.id
        
        invoice = self.env['account.move'].create(invoice_vals)
        
        _logger.info(f"Created prepaid invoice {invoice.name} for contract {contract.name} period {period_string}")
        
        return invoice
