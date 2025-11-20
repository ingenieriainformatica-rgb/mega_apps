# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged
from odoo import Command

@tagged('post_install', '-at_install')
class TestRealnetAnticipos(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env.company
        # Ensure anticipos account exists or create a temporary test account.
        anticipos = self.env['account.account'].search([
            ('code', '=', '28050501'), ('company_id', '=', self.company.id)
        ], limit=1)
        if not anticipos:
            anticipos = self.env['account.account'].create({
                'code': '28050501',
                'name': 'Anticipos de clientes',
                'account_type': 'current_liabilities',
                'company_id': self.company.id,
            })
        self.company.anticipos_customer_account_id = anticipos

        # Customer partner and product
        self.partner = self.env['res.partner'].create({'name': 'Test Customer'})
        receivable = self.partner.property_account_receivable_id
        self.bank_journal = self.env['account.journal'].search([
            ('type', '=', 'bank'), ('company_id', '=', self.company.id)
        ], limit=1)
        if not self.bank_journal:
            self.bank_journal = self.env['account.journal'].create({
                'name': 'Bank Test', 'type': 'bank', 'code': 'TBNK', 'company_id': self.company.id
            })

    def test_payment_from_invoice_keeps_receivable(self):
        inv = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_date': self.env.today(),
            'invoice_line_ids': [
                Command.create({
                    'name': 'Line', 'quantity': 1, 'price_unit': 100.0,
                    'account_id': self.partner.property_account_receivable_id.id,
                })
            ]
        })
        inv.action_post()
        wiz = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=inv.ids).create({})
        payment = wiz._create_payments()
        move = payment.move_id
        partner_lines = move.line_ids.filtered(lambda l: l.partner_id == self.partner and l.account_id == self.partner.property_account_receivable_id)
        self.assertTrue(partner_lines, 'Receivable line should remain on invoice payment')

    def test_standalone_customer_payment_uses_anticipos(self):
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'amount': 50.0,
            'partner_id': self.partner.id,
            'journal_id': self.bank_journal.id,
            'payment_method_line_id': self.bank_journal.inbound_payment_method_line_ids[:1].id,
        })
        payment.action_post()
        move = payment.move_id
        anticipos_account = self.company.anticipos_customer_account_id
        partner_line = move.line_ids.filtered(lambda l: l.partner_id == self.partner and l.account_id == anticipos_account)
        self.assertTrue(partner_line, 'Standalone payment must use anticipos account')

    def test_vendor_payment_unchanged(self):
        vendor = self.env['res.partner'].create({'name': 'Vendor Test', 'supplier_rank': 1})
        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'amount': 10.0,
            'partner_id': vendor.id,
            'journal_id': self.bank_journal.id,
            'payment_method_line_id': self.bank_journal.outbound_payment_method_line_ids[:1].id,
        })
        payment.action_post()
        move = payment.move_id
        payable_line = move.line_ids.filtered(lambda l: l.partner_id == vendor and l.account_id == vendor.property_account_payable_id)
        self.assertTrue(payable_line, 'Vendor payment must remain standard (payable account)')
