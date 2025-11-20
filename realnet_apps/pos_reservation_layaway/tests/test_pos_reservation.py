# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestPosReservation(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})
        self.product = self.env['product.product'].create({'name': 'Test Product', 'list_price': 100.0})
        self.config = self.env['pos.config'].create({'name': 'Test POS'})
        self.journal = self.env['account.journal'].search([('type', 'in', ['cash', 'bank'])], limit=1)

    def test_create_reservation(self):
        payload = {
            'partner_id': self.partner.id,
            'pos_config_id': self.config.id,
            'lines': [
                {'product_id': self.product.id, 'qty': 1, 'price_unit': 100.0, 'discount': 0.0, 'name': 'Test Product'},
            ],
            'initial_payment': {'amount': 20.0, 'journal_id': self.journal.id},
        }
        res = self.env['pos.reservation'].create_from_pos(payload)
        self.assertTrue(res['id'])
        reservation = self.env['pos.reservation'].browse(res['id'])
        self.assertEqual(reservation.amount_total, 100.0)
        self.assertEqual(reservation.state, 'reserved')

