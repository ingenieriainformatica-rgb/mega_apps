# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.mega_account_move_business_fields.hooks import (
    sync_mega_concepto_from_studio,
)


@tagged("post_install", "-at_install")
class TestAccountMoveBusinessFields(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Garantiza la columna de Studio en esta transacción de test (savepoint,
        # se revierte al final), incluso si se corre sobre una BD limpia donde
        # studio_customization nunca creó el campo.
        cls.env.cr.execute(
            "ALTER TABLE account_move ADD COLUMN IF NOT EXISTS x_studio_concepto varchar"
        )
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "sale")], limit=1
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner Concepto"})

    def _create_move(self, **vals):
        move_vals = {
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "journal_id": self.journal.id,
            "invoice_date": fields.Date.today(),
        }
        move_vals.update(vals)
        return self.env["account.move"].create(move_vals)

    def _set_studio_concepto(self, move, value):
        self.env.cr.execute(
            "UPDATE account_move SET x_studio_concepto = %s WHERE id = %s",
            (value, move.id),
        )

    def _get_studio_concepto(self, move):
        self.env.cr.execute(
            "SELECT x_studio_concepto FROM account_move WHERE id = %s", (move.id,)
        )
        return self.env.cr.fetchone()[0]

    # 1. Creación del campo mega_concepto
    def test_01_field_definition(self):
        move = self._create_move()
        move.mega_concepto = "Concepto de prueba"
        self.assertEqual(move.mega_concepto, "Concepto de prueba")

        field = self.env["ir.model.fields"].search(
            [("model", "=", "account.move"), ("name", "=", "mega_concepto")]
        )
        self.assertTrue(field, "El campo mega_concepto no está registrado en ir.model.fields")
        self.assertEqual(field.ttype, "char")
        self.assertTrue(field.store)

    # 2. Copia de datos históricos
    def test_02_migration_copies_historical_data(self):
        move = self._create_move()
        self._set_studio_concepto(move, "Historico Studio")
        move.invalidate_recordset()
        self.assertFalse(move.mega_concepto)

        sync_mega_concepto_from_studio(self.env.cr)

        move.invalidate_recordset()
        self.assertEqual(move.mega_concepto, "Historico Studio")

    # 3. No sobrescribir valores existentes de mega_concepto
    def test_03_does_not_overwrite_existing_mega_concepto(self):
        move = self._create_move(mega_concepto="Valor ya definido")
        self._set_studio_concepto(move, "Otro valor historico")

        sync_mega_concepto_from_studio(self.env.cr)

        move.invalidate_recordset()
        self.assertEqual(move.mega_concepto, "Valor ya definido")

    # 4. Idempotencia: correr la sincronización varias veces no cambia nada
    def test_04_migration_is_idempotent(self):
        move = self._create_move()
        self._set_studio_concepto(move, "Idempotente")

        sync_mega_concepto_from_studio(self.env.cr)
        sync_mega_concepto_from_studio(self.env.cr)
        sync_mega_concepto_from_studio(self.env.cr)

        move.invalidate_recordset()
        self.assertEqual(move.mega_concepto, "Idempotente")
        self.assertEqual(self._get_studio_concepto(move), "Idempotente")

    # 6/11. x_studio_concepto permanece intacto después de sincronizar
    def test_05_old_field_untouched(self):
        move = self._create_move()
        self._set_studio_concepto(move, "No debe borrarse ni cambiar")

        sync_mega_concepto_from_studio(self.env.cr)

        self.assertEqual(self._get_studio_concepto(move), "No debe borrarse ni cambiar")

    # 5. Copia del concepto al duplicar o reversar una factura.
    # No se llama action_post() intencionalmente: este entorno tiene
    # facturación electrónica DIAN activa y postear dispararía integraciones
    # externas irreversibles; _reverse_moves() no exige estado 'posted' para
    # copiar los campos, así que se valida sobre el borrador.
    def test_06_copy_on_duplicate_and_reverse(self):
        move = self._create_move(mega_concepto="Concepto original")

        duplicated = move.copy()
        self.assertEqual(duplicated.mega_concepto, "Concepto original")

        reversed_moves = move._reverse_moves(cancel=False)
        self.assertEqual(reversed_moves.mega_concepto, "Concepto original")

    # 8. Campo relacionado en account.bank.statement.line
    def test_07_bank_statement_line_related_field(self):
        # No se usa account.bank.statement.line.create(): en Odoo 18 postea
        # automáticamente el asiento generado, y este entorno tiene facturación
        # electrónica DIAN (l10n_co_dian) en la cadena de _post() de
        # account.move -no se debe disparar aquí-. Un registro `.new()`
        # (en memoria, nunca escrito en BD) resuelve igual los campos
        # relacionados y valida el mapeo mega_concepto = move_id.mega_concepto
        # sin crear ni postear ningún asiento real.
        move = self.env["account.move"].create({
            "move_type": "entry",
            "date": fields.Date.today(),
            "mega_concepto": "Concepto vía extracto",
        })
        stmt_line = self.env["account.bank.statement.line"].new({"move_id": move.id})
        self.assertEqual(stmt_line.mega_concepto, "Concepto vía extracto")

    # 12. No hay diferencias tras migrar, salvo registros con mega_concepto
    # deliberadamente distinto (verificado en test_03).
    def test_08_no_diff_for_untouched_records(self):
        move = self._create_move()
        self._set_studio_concepto(move, "Igual en ambos")

        sync_mega_concepto_from_studio(self.env.cr)
        move.invalidate_recordset()

        self.assertEqual(move.mega_concepto, self._get_studio_concepto(move))
