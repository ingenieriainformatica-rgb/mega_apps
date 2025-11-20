# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestSlotSelectionLogic(TransactionCase):
    """Test cases for slot selection logic based on slot type and availability"""

    def setUp(self):
        super(TestSlotSelectionLogic, self).setUp()
        
        # Create test data
        self.partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'phone': '123456789',
            'email': 'test@example.com',
        })
        
        # Create parking site
        self.site = self.env['parking.site'].create({
            'name': 'Test Site',
            'city': 'Test City',
        })
        
        # Create location
        self.location = self.env['location.details'].create({
            'name': 'Test Location',
            'address': 'Test Address',
            'city': 'Test City',
            'site_id': self.site.id
        })
        
        # Create slot types
        self.slot_type_moto = self.env['slot.type'].create({
            'name': 'Moto',
            'vehicle_type': 'Moto'
        })
        
        self.slot_type_auto = self.env['slot.type'].create({
            'name': 'Automóvil',
            'vehicle_type': 'Automóvil'
        })
        
        # Create available slots for motos
        self.slot_moto_1 = self.env['slot.details'].create({
            'name': 'M001',
            'code': 'M001',
            'slot_type_id': self.slot_type_moto.id,
            'site_id': self.site.id
        })
        
        self.slot_moto_2 = self.env['slot.details'].create({
            'name': 'M002',
            'code': 'M002',
            'slot_type_id': self.slot_type_moto.id,
            'site_id': self.site.id
        })
        
        # Create available slots for autos
        self.slot_auto_1 = self.env['slot.details'].create({
            'name': 'A001',
            'code': 'A001',
            'slot_type_id': self.slot_type_auto.id,
            'site_id': self.site.id
        })
        
        self.slot_auto_2 = self.env['slot.details'].create({
            'name': 'A002',
            'code': 'A002',
            'slot_type_id': self.slot_type_auto.id,
            'site_id': self.site.id
        })
        
        # Create vehicles
        self.vehicle_moto = self.env['vehicle.details'].create({
            'name': 'Test Moto',
            'number_plate': 'M123',
            'partner_id': self.partner.id
        })
        
        self.vehicle_auto = self.env['vehicle.details'].create({
            'name': 'Test Auto',
            'number_plate': 'A123',
            'partner_id': self.partner.id
        })
        
        # Create a parking entry to occupy one moto slot
        self.occupied_entry = self.env['parking.entry'].create({
            'partner_id': self.partner.id,
            'vehicle_id': self.vehicle_moto.id,
            'slot_type_id': self.slot_type_moto.id,
            'slot_id': self.slot_moto_2.id,
            'location_id': self.location.id,
            'site_id': self.site.id,
        })
        # Check in to occupy the slot
        self.occupied_entry.action_check_in()

    def test_onchange_slot_type_domain_moto(self):
        """Test that onchange for Moto slot type only shows available Moto slots"""
        # Create a new parking entry
        entry = self.env['parking.entry'].new({
            'partner_id': self.partner.id,
            'vehicle_id': self.vehicle_moto.id,
            'site_id': self.site.id,
        })
        
        # Set slot type to Moto
        entry.slot_type_id = self.slot_type_moto
        result = entry.onchange_slot_type_id()
        
        # Check that domain only includes available Moto slots
        expected_domain = [
            ('slot_type_id', '=', self.slot_type_moto.id),
            ('current_parking_entry_id', '=', False),
            ('is_available', '=', True),
            ('site_id', '=', self.site.id)
        ]
        
        self.assertEqual(result['domain']['slot_id'], expected_domain)

    def test_onchange_slot_type_domain_auto(self):
        """Test that onchange for Auto slot type only shows available Auto slots"""
        # Create a new parking entry
        entry = self.env['parking.entry'].new({
            'partner_id': self.partner.id,
            'vehicle_id': self.vehicle_auto.id,
            'site_id': self.site.id,
        })
        
        # Set slot type to Auto
        entry.slot_type_id = self.slot_type_auto
        result = entry.onchange_slot_type_id()
        
        # Check that domain only includes available Auto slots
        expected_domain = [
            ('slot_type_id', '=', self.slot_type_auto.id),
            ('current_parking_entry_id', '=', False),
            ('is_available', '=', True),
            ('site_id', '=', self.site.id)
        ]
        
        self.assertEqual(result['domain']['slot_id'], expected_domain)

    def test_cannot_select_occupied_slot(self):
        """Test that user cannot select an occupied slot"""
        with self.assertRaises(ValidationError):
            self.env['parking.entry'].create({
                'partner_id': self.partner.id,
                'vehicle_id': self.vehicle_moto.id,
                'slot_type_id': self.slot_type_moto.id,
                'slot_id': self.slot_moto_2.id,  # This slot is occupied
                'location_id': self.location.id,
                'site_id': self.site.id,
            })

    def test_cannot_select_wrong_slot_type(self):
        """Test that user cannot select a slot of different type"""
        with self.assertRaises(ValidationError):
            self.env['parking.entry'].create({
                'partner_id': self.partner.id,
                'vehicle_id': self.vehicle_moto.id,
                'slot_type_id': self.slot_type_moto.id,
                'slot_id': self.slot_auto_1.id,  # Auto slot for Moto entry
                'location_id': self.location.id,
                'site_id': self.site.id,
            })

    def test_can_select_available_correct_slot(self):
        """Test that user can select an available slot of the correct type"""
        # This should work without errors (will use default partner)
        entry = self.env['parking.entry'].create({
            'vehicle_id': self.vehicle_moto.id,
            'slot_type_id': self.slot_type_moto.id,
            'slot_id': self.slot_moto_1.id,  # Available Moto slot
            'location_id': self.location.id,
            'site_id': self.site.id,
        })
        
        self.assertEqual(entry.slot_id, self.slot_moto_1)
        self.assertEqual(entry.slot_type_id, self.slot_type_moto)
        # Verify default partner is assigned
        self.assertEqual(entry.partner_id.name, 'Cliente Final')

    def test_slot_becomes_unavailable_after_checkin(self):
        """Test that slot becomes unavailable after check-in"""
        # Create entry with available slot
        entry = self.env['parking.entry'].create({
            'partner_id': self.partner.id,
            'vehicle_id': self.vehicle_auto.id,
            'slot_type_id': self.slot_type_auto.id,
            'slot_id': self.slot_auto_1.id,
            'location_id': self.location.id,
            'site_id': self.site.id,
        })
        
        # Initially slot should be available
        self.assertTrue(self.slot_auto_1.is_available)
        self.assertFalse(self.slot_auto_1.current_parking_entry_id)
        
        # Check in
        entry.action_check_in()
        
        # Refresh slot availability
        self.slot_auto_1.refresh_availability()
        
        # Now slot should be unavailable
        self.assertFalse(self.slot_auto_1.is_available)
        self.assertEqual(self.slot_auto_1.current_parking_entry_id, entry)

    def test_slot_becomes_available_after_checkout(self):
        """Test that slot becomes available after check-out"""
        # Create entry and check in
        entry = self.env['parking.entry'].create({
            'partner_id': self.partner.id,
            'vehicle_id': self.vehicle_auto.id,
            'slot_type_id': self.slot_type_auto.id,
            'slot_id': self.slot_auto_2.id,
            'location_id': self.location.id,
            'site_id': self.site.id,
        })
        
        entry.action_check_in()
        self.slot_auto_2.refresh_availability()
        
        # Slot should be unavailable
        self.assertFalse(self.slot_auto_2.is_available)
        
        # Check out
        entry.action_check_out()
        self.slot_auto_2.refresh_availability()
        
        # Slot should become available again
        self.assertTrue(self.slot_auto_2.is_available)
        self.assertFalse(self.slot_auto_2.current_parking_entry_id)
