# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestDefaultPartner(TransactionCase):
    """Test cases for default partner functionality"""

    def test_default_partner_creation_and_assignment(self):
        """Test that 'Cliente Final' partner is created and assigned by default"""
        
        # Verificar que inicialmente no existe el partner 'Cliente Final'
        existing_partner = self.env['res.partner'].search([('name', '=', 'Cliente Final')])
        if existing_partner:
            existing_partner.unlink()
        
        # Crear un parking entry usando default_get
        defaults = self.env['parking.entry'].default_get(['partner_id', 'name'])
        
        # Verificar que se asignó un partner_id por defecto
        self.assertTrue(defaults.get('partner_id'), "partner_id should be set by default")
        
        # Verificar que el partner creado es 'Cliente Final'
        partner = self.env['res.partner'].browse(defaults['partner_id'])
        self.assertEqual(partner.name, 'Cliente Final', "Default partner should be 'Cliente Final'")
        self.assertTrue(partner.customer_rank > 0, "Default partner should be marked as customer")
        self.assertFalse(partner.is_company, "Default partner should not be a company")

    def test_existing_cliente_final_is_reused(self):
        """Test that existing 'Cliente Final' partner is reused instead of creating duplicates"""
        
        # Crear manualmente el partner 'Cliente Final'
        existing_partner = self.env['res.partner'].create({
            'name': 'Cliente Final',
            'is_company': False,
            'customer_rank': 1,
        })
        
        # Obtener defaults
        defaults = self.env['parking.entry'].default_get(['partner_id'])
        
        # Verificar que se usa el partner existente
        self.assertEqual(defaults['partner_id'], existing_partner.id, 
                        "Should reuse existing 'Cliente Final' partner")
        
        # Verificar que no se crearon duplicados
        partners_count = self.env['res.partner'].search_count([('name', '=', 'Cliente Final')])
        self.assertEqual(partners_count, 1, "Should not create duplicate 'Cliente Final' partners")

    def test_parking_entry_creation_with_default_partner(self):
        """Test complete parking entry creation with default partner"""
        
        # Crear datos de prueba necesarios
        site = self.env['parking.site'].create({
            'name': 'Test Site',
            'city': 'Test City',
        })
        
        location = self.env['location.details'].create({
            'name': 'Test Location',
            'address': 'Test Address',
            'city': 'Test City',
            'site_id': site.id
        })
        
        slot_type = self.env['slot.type'].create({
            'name': 'Auto',
            'vehicle_type': 'Auto'
        })
        
        slot = self.env['slot.details'].create({
            'name': 'A001',
            'code': 'A001',
            'slot_type_id': slot_type.id,
            'site_id': site.id
        })
        
        vehicle = self.env['vehicle.details'].create({
            'name': 'Test Vehicle',
            'number_plate': 'ABC123',
        })
        
        # Crear parking entry (sin especificar partner_id)
        entry = self.env['parking.entry'].create({
            'vehicle_id': vehicle.id,
            'slot_type_id': slot_type.id,
            'slot_id': slot.id,
            'location_id': location.id,
            'site_id': site.id,
        })
        
        # Verificar que se asignó automáticamente 'Cliente Final'
        self.assertEqual(entry.partner_id.name, 'Cliente Final',
                        "Parking entry should have 'Cliente Final' as default partner")
