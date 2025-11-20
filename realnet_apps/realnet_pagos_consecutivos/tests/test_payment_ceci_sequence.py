# -*- coding: utf-8 -*-
from concurrent.futures import ThreadPoolExecutor, as_completed

from odoo import api, fields
from odoo.tests import tagged

# Excepción correcta cuando se viola un UNIQUE en PostgreSQL
try:
    from psycopg2.errors import UniqueViolation as PGUniqueViolation
except Exception:  # fallback si cambia el paquete
    PGUniqueViolation = Exception

# Compatibilidad con frameworks de test
try:
    from odoo.tests.common import SavepointCase as BaseCase
except ImportError:
    from odoo.tests.common import TransactionCase as BaseCase


@tagged('at_install')
class TestPaymentCeciSequence(BaseCase):
    """
    Verifica:
      1) Asignación CE/CI al postear pagos.
      2) Unicidad por compañía vía constraint.
      3) Concurrencia: múltiples hilos posteando pagos no repiten número.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Company = cls.env.company

        # --- Journal banco/caja para pruebas -------------------------------
        journal = cls.env['account.journal'].search([('type', 'in', ('bank', 'cash')),
                                                     ('company_id', '=', cls.Company.id)], limit=1)
        if not journal:
            journal = cls.env['account.journal'].create({
                'name': 'Test Bank',
                'type': 'bank',
                'code': 'TBK',
                'company_id': cls.Company.id,
            })
        cls.journal = journal

        # --- Datos mínimos requeridos por l10n_co_edi en partners ----------
        # Tomamos valores ya válidos del partner de la compañía para evitar violar NOT NULLs.
        comp_partner = cls.Company.partner_id
        base_partner_vals = {
            'company_id': cls.Company.id,
            'country_id': comp_partner.country_id.id,
            'l10n_latam_identification_type_id': comp_partner.l10n_latam_identification_type_id.id,
            'l10n_co_edi_fiscal_regimen': comp_partner.l10n_co_edi_fiscal_regimen,
            'vat': '900123456',  # dummy
        }

        cls.partner_customer = cls.env['res.partner'].create({
            **base_partner_vals,
            'name': 'Cliente Test',
            'customer_rank': 1,
        })
        cls.partner_vendor = cls.env['res.partner'].create({
            **base_partner_vals,
            'name': 'Proveedor Test',
            'supplier_rank': 1,
        })

        # --- Método de cobro/pago (líneas) --------------------------------
        # Creamos líneas manual in/out si no existen.
        in_line = journal.inbound_payment_method_line_ids[:1]
        if not in_line:
            in_line = cls.env['account.payment.method.line'].create({
                'name': 'In M',
                'journal_id': journal.id,
                'payment_method_id': cls.env.ref('account.account_payment_method_manual_in').id,
            })
        out_line = journal.outbound_payment_method_line_ids[:1]
        if not out_line:
            out_line = cls.env['account.payment.method.line'].create({
                'name': 'Out M',
                'journal_id': journal.id,
                'payment_method_id': cls.env.ref('account.account_payment_method_manual_out').id,
            })

        # Guardamos SOLO los IDs (para usarlos desde otros cursores/envs)
        cls.in_method_id = in_line.id
        cls.out_method_id = out_line.id

    # -------------------------- Helpers -----------------------------------

    def _create_and_post(self, *, payment_type, partner, amount=100.0):
        """Crea y publica un pago en el cursor/entorno actual."""
        method_line_id = self.in_method_id if payment_type == 'inbound' else self.out_method_id
        pay = self.env['account.payment'].create({
            'payment_type': payment_type,              # inbound (cliente) / outbound (proveedor)
            'partner_id': partner.id,
            'journal_id': self.journal.id,
            'payment_method_line_id': method_line_id,
            'amount': amount,
            'date': fields.Date.today(),
        })
        pay.action_post()
        self.assertTrue(pay.x_ceci_number, "El pago debe quedar numerado (x_ceci_number).")
        return pay

    def _post_in_new_cursor(self, *, payment_type, partner, amount=100.0):
        """Abre un cursor propio para simular otro usuario/hilo (concurrencia)."""
        with self.env.registry.cursor() as cr2:
            env2 = api.Environment(cr2, self.env.uid, dict(self.env.context, company_id=self.Company.id))
            Payment = env2['account.payment']
            method_line_id = self.in_method_id if payment_type == 'inbound' else self.out_method_id
            pay = Payment.create({
                'payment_type': payment_type,
                'partner_id': partner.id,
                'journal_id': self.journal.id,
                'payment_method_line_id': method_line_id,
                'amount': amount,
                'date': fields.Date.today(),
            })
            pay.action_post()
            return pay.id

    # ---------------------------- Tests -----------------------------------

    def test_01_single_post_assigns_number(self):
        p_in = self._create_and_post(payment_type='inbound', partner=self.partner_customer)
        self.assertTrue(p_in.x_ceci_number.startswith('CI'), "Ingresos deberían prefijar CI.")
        p_out = self._create_and_post(payment_type='outbound', partner=self.partner_vendor)
        self.assertTrue(p_out.x_ceci_number.startswith('CE'), "Egresos deberían prefijar CE.")

    def test_02_unique_constraint_blocks_duplicates(self):
        p1 = self._create_and_post(payment_type='inbound', partner=self.partner_customer)
        p2 = self._create_and_post(payment_type='inbound', partner=self.partner_customer)
        # Forzamos número duplicado por SQL para disparar el UNIQUE de tu módulo.
        with self.assertRaises(PGUniqueViolation):
            self.cr.execute(
                "UPDATE account_payment SET x_ceci_number=%s WHERE id=%s",
                (p1.x_ceci_number, p2.id),
            )

    def test_03_concurrency_many_users_get_unique_numbers(self):
        """Simula N usuarios posteando en paralelo y verifica no-duplicidad."""
        N = 20
        futures = []
        with ThreadPoolExecutor(max_workers=8) as ex:
            for i in range(N):
                if i % 2:
                    fut = ex.submit(
                        self._post_in_new_cursor,
                        payment_type='inbound', partner=self.partner_customer, amount=10 + i
                    )
                else:
                    fut = ex.submit(
                        self._post_in_new_cursor,
                        payment_type='outbound', partner=self.partner_vendor, amount=10 + i
                    )
                futures.append(fut)

            # recolectar los ids (as_completed garantiza esperar a todos)
            ids = [f.result() for f in as_completed(futures)]

        pays = self.env['account.payment'].browse(ids)
        numbers = pays.mapped('x_ceci_number')
        self.assertEqual(len(numbers), N)
        self.assertEqual(len(set(numbers)), N, "No debe haber números CE/CI repetidos bajo concurrencia.")
