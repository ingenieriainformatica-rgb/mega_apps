# -*- coding: utf-8 -*-
"""Pruebas de mega_credit_note_copy_invoice_data.

Cada metodo esta numerado para poder mapearlo contra la matriz de pruebas
obligatorias del encargo (copia del campo 'vehicle' de factura a nota
credito, y el asistente historico mega.credit.note.vehicle.backfill.wizard).

Nota de entorno: esta base es un clon de una copia de produccion con
l10n_co_edi_jorels instalado, y ese modulo tiene 'ei_enable' en True por
defecto en toda compania nueva. Si quedara activo, contabilizar una factura
dispararia el envio electronico real a la API de Jorels. Por eso
setUpClass desactiva 'ei_enable' en la compania de pruebas: el cambio vive
dentro de la transaccion de la prueba (TransactionCase hace rollback al
terminar) y nunca se persiste.
"""
from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestCreditNoteCopyInvoiceData(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        if 'ei_enable' in cls.env['res.company']._fields:
            cls.company.write({'ei_enable': False})

        cls.sale_journal = cls.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', cls.company.id)], limit=1)
        cls.purchase_journal = cls.env['account.journal'].search(
            [('type', '=', 'purchase'), ('company_id', '=', cls.company.id)], limit=1)

        # country_id extranjero para que la validacion colombiana de
        # identificacion (mega_contact_lock_identification) no exija
        # NIT/cedula en estos contactos de prueba.
        foreign_country = cls.env.ref('base.us')
        cls.customer = cls.env['res.partner'].create({
            'name': 'Cliente Prueba Vehiculo', 'country_id': foreign_country.id,
        })
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Proveedor Prueba Vehiculo', 'country_id': foreign_country.id,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Servicio de prueba mega_credit_note_copy_invoice_data',
            'list_price': 100.0,
        })

        cls.backfill_group = cls.env.ref(
            'mega_credit_note_copy_invoice_data.group_credit_note_vehicle_backfill')

    # -- helpers ---------------------------------------------------------

    def _create_invoice(self, move_type, partner, vehicle=False, date=None):
        journal = self.sale_journal if move_type == 'out_invoice' else self.purchase_journal
        move = self.env['account.move'].create({
            'move_type': move_type,
            'partner_id': partner.id,
            'journal_id': journal.id,
            'invoice_date': date or fields.Date.today(),
            'vehicle': vehicle,
            'invoice_line_ids': [Command.create({
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100.0,
            })],
        })
        move.action_post()
        return move

    def _reverse(self, moves, extra_vals=None):
        # Se usa Form (en vez de un .create(vals) crudo) para reproducir
        # fielmente el flujo real del boton "Nota de credito": default_get()
        # y los compute (p.ej. journal_id) del wizard estandar solo se
        # completan de forma confiable a traves del ciclo onchange/Form,
        # igual que lo haria el cliente web.
        wizard_form = Form(self.env['account.move.reversal'].with_context(
            active_model='account.move', active_ids=moves.ids,
        ))
        for field_name, value in (extra_vals or {}).items():
            setattr(wizard_form, field_name, value)
        wizard = wizard_form.save()
        wizard.reverse_moves()
        return wizard

    def _create_historic_pair(self, vehicle_invoice='HIST-1', vehicle_note=False, move_type='out_invoice'):
        """Crea una factura + su nota credito 'tal cual quedaria' antes de
        instalar este modulo (vehicle vacio en la nota), para probar el
        asistente de actualizacion historica."""
        partner = self.customer if move_type == 'out_invoice' else self.vendor
        invoice = self._create_invoice(move_type, partner, vehicle=vehicle_invoice)
        wizard = self._reverse(invoice)
        note = wizard.new_move_ids
        note.write({'vehicle': vehicle_note})
        return invoice, note

    def _make_authorized_user(self, login='backfill_authorized@example.com'):
        return self.env['res.users'].create({
            'name': 'Usuario Autorizado Backfill',
            'login': login,
            'email': login,
            'groups_id': [
                Command.link(self.env.ref('base.group_user').id),
                Command.link(self.env.ref('account.group_account_invoice').id),
                Command.link(self.backfill_group.id),
            ],
        })

    # -- 1: factura de cliente con vehiculo -> nota credito total --------

    def test_01_customer_invoice_full_credit_note_copies_vehicle(self):
        invoice = self._create_invoice('out_invoice', self.customer, vehicle='ABC123')
        wizard = self._reverse(invoice)
        credit_note = wizard.new_move_ids
        self.assertEqual(len(credit_note), 1)
        self.assertEqual(credit_note.reversed_entry_id, invoice)
        self.assertEqual(credit_note.vehicle, 'ABC123')

    # -- 2: factura de cliente con vehiculo -> nota credito parcial ------

    def test_02_customer_invoice_partial_credit_note_keeps_vehicle(self):
        invoice = self._create_invoice('out_invoice', self.customer, vehicle='XYZ999')
        wizard = self._reverse(invoice)
        credit_note = wizard.new_move_ids
        self.assertEqual(credit_note.state, 'draft')
        # Nota credito parcial: se reduce la cantidad antes de confirmarla.
        credit_note.invoice_line_ids.write({'quantity': 0.5})
        self.assertEqual(credit_note.vehicle, 'XYZ999')
        invoice.invalidate_recordset()
        self.assertEqual(invoice.vehicle, 'XYZ999')

    # -- 3: factura de proveedor con vehiculo -> nota credito ------------

    def test_03_vendor_bill_credit_note_copies_vehicle(self):
        bill = self._create_invoice('in_invoice', self.vendor, vehicle='PROV-001')
        wizard = self._reverse(bill)
        credit_note = wizard.new_move_ids
        self.assertEqual(credit_note.move_type, 'in_refund')
        self.assertEqual(credit_note.vehicle, 'PROV-001')

    # -- 4: factura sin vehiculo -> nota credito sin vehiculo ------------

    def test_04_invoice_without_vehicle_credit_note_without_vehicle(self):
        invoice = self._create_invoice('out_invoice', self.customer, vehicle=False)
        wizard = self._reverse(invoice)
        credit_note = wizard.new_move_ids
        self.assertFalse(credit_note.vehicle)

    # -- 5/6: reversion multiple, cada nota conserva su propio vehiculo --

    def test_05_batch_reversal_keeps_each_own_vehicle(self):
        invoice_a = self._create_invoice('out_invoice', self.customer, vehicle='CAR-A')
        invoice_b = self._create_invoice('out_invoice', self.customer, vehicle='CAR-B')
        wizard = self._reverse(invoice_a + invoice_b)
        credit_notes = wizard.new_move_ids
        self.assertEqual(len(credit_notes), 2)
        note_a = credit_notes.filtered(lambda m: m.reversed_entry_id == invoice_a)
        note_b = credit_notes.filtered(lambda m: m.reversed_entry_id == invoice_b)
        self.assertEqual(note_a.vehicle, 'CAR-A')
        self.assertEqual(note_b.vehicle, 'CAR-B')

    # -- 7: nota credito manual sin factura origen ------------------------

    def test_07_manual_credit_note_without_origin_stays_empty(self):
        manual_note = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.customer.id,
            'journal_id': self.sale_journal.id,
            'invoice_date': fields.Date.today(),
        })
        self.assertFalse(manual_note.reversed_entry_id)
        self.assertFalse(manual_note.vehicle)

    # -- 8/9: compatibilidad con el override de l10n_co_edi_jorels --------

    def test_08_09_compatibility_with_jorels_dian_override(self):
        jorels_installed = self.env['ir.module.module'].sudo().search([
            ('name', '=', 'l10n_co_edi_jorels'), ('state', '=', 'installed'),
        ])
        if not jorels_installed:
            self.skipTest('l10n_co_edi_jorels no esta instalado en esta base de pruebas')

        concept = self.env['l10n_co_edi_jorels.correction_concepts'].search(
            [('type_document_id', '=', 5)], limit=1)
        invoice = self._create_invoice('out_invoice', self.customer, vehicle='JORELS-1')
        extra_vals = {}
        if concept:
            extra_vals['ei_correction_concept_credit_id'] = concept
        wizard = self._reverse(invoice, extra_vals=extra_vals)
        credit_note = wizard.new_move_ids

        # Nuestro campo se copio...
        self.assertEqual(credit_note.vehicle, 'JORELS-1')
        # ...y el override existente de l10n_co_edi_jorels se sigue ejecutando
        # (super() encadenado correctamente entre ambos modulos).
        self.assertEqual(credit_note.is_out_country, invoice.is_out_country)
        if concept:
            self.assertEqual(credit_note.ei_correction_concept_credit_id, concept)

    # -- 10: no se copian CUFE/estado DIAN/XML/adjuntos ------------------

    def test_10_no_dian_technical_fields_copied(self):
        invoice = self._create_invoice('out_invoice', self.customer, vehicle='NODIAN')
        wizard = self._reverse(invoice)
        credit_note = wizard.new_move_ids

        if 'l10n_co_dian_document_ids' in credit_note._fields:
            self.assertFalse(credit_note.l10n_co_dian_document_ids)
            self.assertFalse(credit_note.l10n_co_edi_cufe_cude_ref)
        if 'ei_uuid' in credit_note._fields:
            self.assertFalse(credit_note.ei_uuid)
            self.assertFalse(credit_note.ei_zip_key)
            self.assertFalse(credit_note.ei_xml_base64_bytes)

    # -- 11: no cambian lineas, impuestos, totales, ni la factura origen -

    def test_11_lines_taxes_totals_unchanged(self):
        invoice = self._create_invoice('out_invoice', self.customer, vehicle='TOTALS-1')
        original_total = invoice.amount_total
        original_line_count = len(invoice.invoice_line_ids)

        wizard = self._reverse(invoice)
        credit_note = wizard.new_move_ids

        self.assertEqual(len(credit_note.invoice_line_ids), original_line_count)
        self.assertAlmostEqual(credit_note.amount_total, original_total)

        invoice.invalidate_recordset()
        self.assertEqual(invoice.amount_total, original_total)
        self.assertEqual(len(invoice.invoice_line_ids), original_line_count)
        self.assertEqual(invoice.vehicle, 'TOTALS-1')

    # Nota sobre las pruebas 12-19: esta base de pruebas es un clon de una
    # copia de produccion, que ya contiene cientos de notas credito
    # historicas reales que calzan con el dominio del asistente. Por eso
    # los conteos agregados (count_found/count_to_update/count_skipped) no
    # se comparan contra numeros absolutos: se verifica membresia del
    # registro creado por la propia prueba dentro de los conjuntos
    # encontrado/por-actualizar/omitido que calcula _split_candidates().

    # -- 12: la vista previa del asistente historico no escribe ----------

    def test_12_preview_does_not_write(self):
        invoice, note = self._create_historic_pair(vehicle_invoice='HIST-12')
        user = self._make_authorized_user('backfill_12@example.com')
        wiz = self.env['mega.credit.note.vehicle.backfill.wizard'].with_user(user).create({})
        wiz.action_preview()

        found, to_update = wiz._split_candidates()
        self.assertIn(note.id, found.ids)
        self.assertIn(note.id, to_update.ids)

        note.invalidate_recordset()
        self.assertFalse(note.vehicle)
        self.assertEqual(wiz.state, 'preview')
        self.assertEqual(wiz.count_found, len(found))
        self.assertEqual(wiz.count_to_update, len(to_update))

    # -- 13: la ejecucion llena el vehiculo vacio -------------------------

    def test_13_update_fills_empty_vehicle(self):
        invoice, note = self._create_historic_pair(vehicle_invoice='HIST-13')
        user = self._make_authorized_user('backfill_13@example.com')
        wiz = self.env['mega.credit.note.vehicle.backfill.wizard'].with_user(user).create({})
        wiz.action_preview()
        wiz.action_update()

        note.invalidate_recordset()
        self.assertEqual(note.vehicle, 'HIST-13')
        self.assertTrue(note.message_ids.filtered(
            lambda m: 'recuperado desde la factura origen' in (m.body or '')
        ))

    # -- 14: no sobrescribe una nota que ya tiene vehiculo ----------------

    def test_14_does_not_overwrite_existing_vehicle(self):
        invoice, note = self._create_historic_pair(vehicle_invoice='HIST-NEW', vehicle_note='YA-TENIA')
        user = self._make_authorized_user('backfill_14@example.com')
        wiz = self.env['mega.credit.note.vehicle.backfill.wizard'].with_user(user).create({})
        wiz.action_preview()

        found, to_update = wiz._split_candidates()
        self.assertIn(note.id, found.ids)
        self.assertNotIn(note.id, to_update.ids)

        wiz.action_update()
        note.invalidate_recordset()
        self.assertEqual(note.vehicle, 'YA-TENIA')

    # -- 15: omite cuando la factura origen no tiene vehiculo -------------

    def test_15_skips_note_when_origin_has_no_vehicle(self):
        invoice, note = self._create_historic_pair(vehicle_invoice=False, vehicle_note=False)
        user = self._make_authorized_user('backfill_15@example.com')
        wiz = self.env['mega.credit.note.vehicle.backfill.wizard'].with_user(user).create({})
        wiz.action_preview()

        _found, to_update = wiz._split_candidates()
        self.assertNotIn(note.id, to_update.ids)

        wiz.action_update()
        note.invalidate_recordset()
        self.assertFalse(note.vehicle)

    # -- 16: omite notas sin reversed_entry_id -----------------------------

    def test_16_skips_notes_without_reversed_entry(self):
        manual_note = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.customer.id,
            'journal_id': self.sale_journal.id,
        })
        wiz = self.env['mega.credit.note.vehicle.backfill.wizard'].create({})
        found_ids = self.env['account.move'].search(wiz._get_domain()).ids
        self.assertNotIn(manual_note.id, found_ids)

    # -- 17: usuario sin el grupo recibe AccessError ----------------------

    def test_17_unauthorized_user_gets_access_error(self):
        unauthorized = self.env['res.users'].create({
            'name': 'Usuario Sin Permiso',
            'login': 'sin_permiso_backfill@example.com',
            'email': 'sin_permiso_backfill@example.com',
            'groups_id': [
                Command.link(self.env.ref('base.group_user').id),
                Command.link(self.env.ref('account.group_account_invoice').id),
            ],
        })
        with self.assertRaises(AccessError):
            self.env['mega.credit.note.vehicle.backfill.wizard'].with_user(unauthorized).create({})

    # -- 18: ejecutarlo dos veces no vuelve a modificar nada ---------------

    def test_18_running_twice_is_idempotent(self):
        invoice, note = self._create_historic_pair(vehicle_invoice='HIST-18')
        user = self._make_authorized_user('backfill_18@example.com')

        wiz = self.env['mega.credit.note.vehicle.backfill.wizard'].with_user(user).create({})
        wiz.action_preview()
        wiz.action_update()
        note.invalidate_recordset()
        message_count_after_first = len(note.message_ids)
        self.assertEqual(note.vehicle, 'HIST-18')

        wiz2 = self.env['mega.credit.note.vehicle.backfill.wizard'].with_user(user).create({})
        wiz2.action_preview()
        _found2, to_update2 = wiz2._split_candidates()
        self.assertNotIn(note.id, to_update2.ids)
        wiz2.action_update()

        note.invalidate_recordset()
        self.assertEqual(note.vehicle, 'HIST-18')
        self.assertEqual(len(note.message_ids), message_count_after_first)

    # -- 19: filtros por fecha y tipo de nota -------------------------------

    def test_19_date_and_type_filters(self):
        today = fields.Date.today()
        _invoice, note = self._create_historic_pair(vehicle_invoice='FILTER-CUST')
        _bill, vendor_note = self._create_historic_pair(vehicle_invoice='FILTER-VEND', move_type='in_invoice')

        wiz_customers = self.env['mega.credit.note.vehicle.backfill.wizard'].create({'note_type': 'customer'})
        found_ids = self.env['account.move'].search(wiz_customers._get_domain()).ids
        self.assertIn(note.id, found_ids)
        self.assertNotIn(vendor_note.id, found_ids)

        wiz_vendors = self.env['mega.credit.note.vehicle.backfill.wizard'].create({'note_type': 'vendor'})
        found_ids = self.env['account.move'].search(wiz_vendors._get_domain()).ids
        self.assertIn(vendor_note.id, found_ids)
        self.assertNotIn(note.id, found_ids)

        wiz_past = self.env['mega.credit.note.vehicle.backfill.wizard'].create({
            'note_type': 'both',
            'date_to': today - timedelta(days=1),
        })
        found_ids = self.env['account.move'].search(wiz_past._get_domain()).ids
        self.assertNotIn(note.id, found_ids)
        self.assertNotIn(vendor_note.id, found_ids)

        wiz_today = self.env['mega.credit.note.vehicle.backfill.wizard'].create({
            'note_type': 'both',
            'date_from': today,
            'date_to': today,
        })
        found_ids = self.env['account.move'].search(wiz_today._get_domain()).ids
        self.assertIn(note.id, found_ids)
        self.assertIn(vendor_note.id, found_ids)
