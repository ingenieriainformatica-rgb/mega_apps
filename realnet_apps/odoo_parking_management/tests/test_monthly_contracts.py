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
from datetime import date, timedelta
from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestMonthlyContracts(TransactionCase):
    """Test monthly parking contracts functionality"""

    def setUp(self):
        super().setUp()
        
        # Create test data
        self.partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'test@example.com'
        })
        
        self.site = self.env['parking.site'].create({
            'name': 'Test Site',
            'city': 'medellin'  # Use valid city selection
        })
        
        self.product = self.env['product.product'].create({
            'name': 'Monthly Parking Plan',
            'type': 'service',
            'list_price': 100.0,
            'sale_ok': True
        })
        
        self.contract = self.env['parking.monthly.contract'].create({
            'name': 'Test Contract',
            'partner_id': self.partner.id,
            'site_id': self.site.id,
            'plan_product_id': self.product.id,
            'price_unit': 150.0,
            'recurring_day': '1',
            'start_date': date.today()
        })

    def test_contract_creation(self):
        """Test basic contract creation"""
        self.assertEqual(self.contract.state, 'draft')
        self.assertEqual(self.contract.price_unit, 150.0)
        self.assertEqual(self.contract.partner_id, self.partner)
        self.assertEqual(self.contract.site_id, self.site)

    def test_contract_activation(self):
        """Test contract activation"""
        self.contract.action_activate()
        self.assertEqual(self.contract.state, 'active')

    def test_unique_active_contract_constraint(self):
        """Test that only one active contract per partner+site is allowed"""
        self.contract.action_activate()
        
        # Try to create another active contract for same partner+site
        with self.assertRaises(ValidationError):
            duplicate_contract = self.env['parking.monthly.contract'].create({
                'name': 'Duplicate Contract',
                'partner_id': self.partner.id,
                'site_id': self.site.id,
                'plan_product_id': self.product.id,
                'price_unit': 200.0,
                'recurring_day': '15',
                'start_date': date.today()
            })
            duplicate_contract.action_activate()

    def test_find_active_contract(self):
        """Test finding active contracts"""
        self.contract.action_activate()
        
        found_contract = self.env['parking.monthly.contract'].find_active_contract(
            self.partner.id, self.site.id
        )
        
        self.assertEqual(found_contract, self.contract)

    def test_prepaid_contract_creation_and_activation(self):
        """Test prepaid contract creation and automatic invoice generation"""
        # Create prepaid contract
        prepaid_contract = self.env['parking.monthly.contract'].create({
            'name': 'Prepaid Contract',
            'partner_id': self.partner.id,
            'site_id': self.site.id,
            'plan_product_id': self.product.id,
            'price_unit': 250.0,
            'billing_mode': 'prepaid',
            'recurring_day': '15',
            'start_date': date.today()
        })
        
        self.assertEqual(prepaid_contract.billing_mode, 'prepaid')
        self.assertEqual(prepaid_contract.state, 'draft')
        
        # Check no invoices exist before activation
        invoices_before = self.env['account.move'].search([
            ('partner_id', '=', self.partner.id),
            ('parking_site_id', '=', self.site.id),
            ('billing_mode', '=', 'prepaid')
        ])
        self.assertEqual(len(invoices_before), 0)
        
        # Activate contract
        prepaid_contract.action_activate()
        self.assertEqual(prepaid_contract.state, 'active')
        
        # Check that prepaid invoice was created
        invoices_after = self.env['account.move'].search([
            ('partner_id', '=', self.partner.id),
            ('parking_site_id', '=', self.site.id),
            ('billing_mode', '=', 'prepaid')
        ])
        self.assertEqual(len(invoices_after), 1)
        
        invoice = invoices_after[0]
        self.assertEqual(invoice.monthly_contract_id, prepaid_contract)
        self.assertEqual(invoice.billing_mode, 'prepaid')
        self.assertEqual(len(invoice.invoice_line_ids), 1)  # Single line for plan
        self.assertEqual(invoice.invoice_line_ids[0].price_unit, 250.0)

    def test_prepaid_vs_postpaid_ticket_handling(self):
        """Test that prepaid contracts don't aggregate tickets to invoices"""
        # Create slot_type for testing
        slot_type = self.env['slot.type'].create({
            'vehicle_type': 'Auto',
            'code': 'AUTO'
        })
        
        # Create prepaid contract
        prepaid_contract = self.env['parking.monthly.contract'].create({
            'name': 'Prepaid Contract',
            'partner_id': self.partner.id,
            'site_id': self.site.id,
            'plan_product_id': self.product.id,
            'price_unit': 250.0,
            'billing_mode': 'prepaid',
            'recurring_day': '15',
            'start_date': date.today()
        })
        prepaid_contract.action_activate()
        
        # Create postpaid contract for same partner but different site
        site2 = self.env['parking.site'].create({
            'name': 'Site 2',
            'city': 'medellin'
        })
        
        postpaid_contract = self.env['parking.monthly.contract'].create({
            'name': 'Postpaid Contract',
            'partner_id': self.partner.id,
            'site_id': site2.id,
            'plan_product_id': self.product.id,
            'price_unit': 200.0,
            'billing_mode': 'postpaid',
            'recurring_day': '15',
            'start_date': date.today()
        })
        postpaid_contract.action_activate()
        
        # Create parking entries for both contracts
        entry1 = self.env['parking.entry'].create({
            'partner_id': self.partner.id,
            'site_id': self.site.id,
            'slot_type_id': slot_type.id,
            'product_id': self.product.id,
            'state': 'check_out'
        })
        
        entry2 = self.env['parking.entry'].create({
            'partner_id': self.partner.id,
            'site_id': site2.id,
            'slot_type_id': slot_type.id,
            'product_id': self.product.id,
            'state': 'check_out'
        })
        
        # Process monthly entries
        monthly_service = self.env['parking.monthly.service']
        result1 = monthly_service.add_entry_to_monthly_invoice(entry1)  # Prepaid - should return False
        result2 = monthly_service.add_entry_to_monthly_invoice(entry2)  # Postpaid - should return invoice
        
        self.assertFalse(result1, "Prepaid entries should not be added to invoices")
        self.assertTrue(result2, "Postpaid entries should be added to invoices")
        
        # Verify that prepaid entry has no monthly_invoice_id
        self.assertFalse(entry1.monthly_invoice_id)
        # Verify that postpaid entry has monthly_invoice_id
        self.assertTrue(entry2.monthly_invoice_id)

    def test_period_key_generation(self):
        """Test period key generation"""
        period_key = self.contract.get_period_key()
        self.assertEqual(len(period_key), 6)  # contract_id, site_id, partner_id, company_id, year, month
        
        period_string = self.contract.get_period_string()
        import re
        self.assertTrue(re.match(r'\d{4}-\d{2}', period_string))

    def test_contract_stats(self):
        """Test contract statistics computation"""
        self.contract._compute_entry_stats()
        self.assertEqual(self.contract.total_entries_count, 0)
        self.assertEqual(self.contract.current_month_entries_count, 0)


class TestMonthlyInvoicing(TransactionCase):
    """Test monthly invoice aggregation functionality"""

    def setUp(self):
        super().setUp()
        
        # Create test data
        self.partner = self.env['res.partner'].create({
            'name': 'Monthly Customer',
            'email': 'monthly@example.com'
        })
        
        self.site = self.env['parking.site'].create({
            'name': 'Monthly Site',
            'city': 'bogota'  # Use valid city selection
        })
        
        self.location = self.env['location.details'].create({
            'name': 'Monthly Location',
            'city': 'bogota'  # Use valid city selection
        })
        
        self.product = self.env['product.product'].create({
            'name': 'Monthly Plan',
            'type': 'service',
            'list_price': 200.0,
            'sale_ok': True
        })
        
        self.slot_type = self.env['slot.type'].create({
            'vehicle_type': 'Auto',
            'code': 'AUTO'
        })
        
        self.slot = self.env['slot.details'].create({
            'name': 'Slot-001',
            'slot_type_id': self.slot_type.id,
            'site_id': self.site.id
        })
        
        self.vehicle = self.env['vehicle.details'].create({
            'vehicle_name': 'Automovil',
            'number_plate': 'ABC123'
        })
        
        self.contract = self.env['parking.monthly.contract'].create({
            'name': 'Monthly Contract',
            'partner_id': self.partner.id,
            'site_id': self.site.id,
            'plan_product_id': self.product.id,
            'price_unit': 200.0,
            'recurring_day': '1',
            'start_date': date.today(),
            'state': 'active'
        })

    def test_monthly_invoice_creation(self):
        """Test monthly invoice creation"""
        service = self.env['parking.monthly.service']
        invoice = service._get_or_create_monthly_invoice(self.contract)
        
        self.assertTrue(invoice)
        self.assertEqual(invoice.partner_id, self.partner)
        self.assertEqual(invoice.monthly_contract_id, self.contract)
        self.assertEqual(invoice.parking_site_id, self.site)

    def test_parking_entry_aggregation(self):
        """Test parking entry aggregation to monthly invoice"""
        # Create parking entry
        entry = self.env['parking.entry'].create({
            'partner_id': self.partner.id,
            'site_id': self.site.id,
            'location_id': self.location.id,
            'vehicle_id': self.vehicle.id,
            'slot_type_id': self.slot_type.id,
            'slot_id': self.slot.id
        })
        
        # Entry should be marked as monthly
        self.assertTrue(entry.is_monthly)
        self.assertEqual(entry.monthly_contract_id, self.contract)
        
        # Simulate check-out to trigger aggregation
        entry.action_check_in()
        entry.action_check_out()
        
        # Entry should have a monthly invoice
        self.assertTrue(entry.monthly_invoice_id)
        self.assertEqual(entry.monthly_invoice_id.monthly_contract_id, self.contract)

    def test_unique_invoice_per_period(self):
        """Test that only one invoice is created per contract per period"""
        service = self.env['parking.monthly.service']
        
        # Create first invoice
        invoice1 = service._get_or_create_monthly_invoice(self.contract)
        
        # Try to create second invoice for same period
        invoice2 = service._get_or_create_monthly_invoice(self.contract)
        
        # Should return the same invoice
        self.assertEqual(invoice1, invoice2)


class TestMonthlyDashboard(TransactionCase):
    """Test monthly dashboard functionality"""

    def setUp(self):
        super().setUp()
        
        self.site = self.env['parking.site'].create({
            'name': 'Dashboard Site',
            'city': 'cucuta'  # Use valid city selection
        })
        
        self.dashboard = self.env['parking.monthly.dashboard'].create({
            'site_id': self.site.id,
            'period_month': date.today()
        })

    def test_dashboard_creation(self):
        """Test dashboard creation and metric computation"""
        self.assertEqual(self.dashboard.site_id, self.site)
        self.assertEqual(self.dashboard.active_contracts_count, 0)
        self.assertEqual(self.dashboard.expired_contracts_count, 0)

    def test_dashboard_actions(self):
        """Test dashboard action methods"""
        # Test view actions
        action = self.dashboard.action_view_active_contracts()
        self.assertEqual(action['res_model'], 'parking.monthly.contract')
        
        action = self.dashboard.action_view_monthly_invoices()
        self.assertEqual(action['res_model'], 'account.move')

    def test_get_dashboard_data(self):
        """Test dashboard data API"""
        data = self.env['parking.monthly.dashboard'].get_dashboard_data(
            self.site.id, date.today()
        )
        
        self.assertIn('site_id', data)
        self.assertIn('active_contracts_count', data)
        self.assertIn('recurring_revenue', data)
        self.assertEqual(data['site_id'], self.site.id)
