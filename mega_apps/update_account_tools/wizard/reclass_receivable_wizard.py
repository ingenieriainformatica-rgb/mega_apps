import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ReclassReceivableWizard(models.TransientModel):
    _name = 'realnet.reclass.receivable.wizard'
    _description = 'Reclasificación CxC por cuenta origen/destino'

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        string='Compañía',
    )
    account_src_id = fields.Many2one(
        'account.account',
        string='Cuenta origen',
        required=True,
        # domain="[('code', 'in', ['130500','413506','613500','413504','210500','210505','220500','220505'])]",

    )
    account_dst_id = fields.Many2one(
        'account.account',
        string='Cuenta destino',
        required=True,
        # domain="[('code', 'in', ['13050501'])]",
    )
    date_from = fields.Date(string='Desde')
    date_to = fields.Date(string='Hasta')
    include_paid = fields.Boolean(string='Incluir pagadas', default=False)
    invoice_id = fields.Many2one(
        'account.move',
        string='Factura (por cuenta origen)',
        # Dominio base: siempre reduce a facturas cliente publicadas y de la compañía
        help='Muestra solo facturas que tienen líneas en la cuenta origen y cumplen el resto de filtros.'
    )
    # domain="[('move_type','in',('out_invoice','out_refund')), ('state','=','posted')]",
    # Modo bulk
    bulk_mode = fields.Boolean("Reclasificar en BULK", default=False)
    journal_id = fields.Many2one(
        'account.journal',
        string='Diario',
        domain="[('company_id', '=', company_id)]",
    )

    def _prepare_domain(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        AML = self.env['account.move.line'].with_company(company)
        acc_src = self.account_src_id.with_company(company)
        acc_dst = self.account_dst_id.with_company(company)

        domain = [
            ('company_id', '=', company.id),
            ('account_id', '=', acc_src.id),
            ('move_id.state', '=', 'posted'),
        ]
        if self.invoice_id:
            domain.append(('move_id', '=', self.invoice_id.id))
        else:
            if self.date_from:
                domain.append(('date', '>=', self.date_from))
            if self.date_to:
                domain.append(('date', '<=', self.date_to))
            if not self.include_paid:
                domain.append(('amount_residual', '!=', 0.0))

        return AML, acc_src, acc_dst, domain

    def action_confirm(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        AML, acc_src, acc_dst, domain = self._prepare_domain()

        # Modo puntual: usar la lógica shell interna
        if self.invoice_id:
            move = self.invoice_id
            _logger.info(f"\n\n 1 {move} \n\n")
            if move.state != 'posted' or move.move_type not in ('out_invoice', 'out_refund'):
                raise UserError(_('La factura debe estar en estado Registrado y ser de cliente.'))
            _logger.info(f"\n\n 2 \n\n")
            return self._reclass_update_invoice_sql(move, acc_src, acc_dst, company)

    def _reclass_update_invoice_sql(self, move, acc_src, acc_dst, compan):
        """
        UPDATE directo por SQL:
        - Cambia la cuenta de la(s) línea(s) CxC de la factura y de sus pagos conciliados
        - Respalda en x_backup_move_line_account
        - Más tolerante: si acc_src viene vacío, detecta CxC por partner+tipo; si viene, filtra por cuenta exacta
        """
        self.ensure_one()
        if not move or not acc_dst:
            raise UserError("Debes enviar la factura (move) y la cuenta destino (acc_dst).")

        cr = self.env.cr
        # 1) backup table
        cr.execute("""
            CREATE TABLE IF NOT EXISTS x_backup_move_line_account (
                id              bigserial PRIMARY KEY,
                run_at          timestamptz NOT NULL DEFAULT now(),
                move_line_id    int NOT NULL,
                old_account_id  int NOT NULL,
                new_account_id  int NOT NULL,
                note            text
            )
        """)

        inv_move_id = move.id
        partner_id  = move.partner_id.id or None
        acc_src_id  = acc_src.id if acc_src else None
        acc_dst_id  = acc_dst.id
        note        = f"sql-change for invoice {move.name}"

        _logger.info("SQL UPDATE CxC → factura=%s(id=%s) origen=%s destino=%s cia=%s",
                    move.name, inv_move_id, getattr(acc_src, "code", None),
                    getattr(acc_dst, "code", None), compan.display_name)

        # 2) ¿Qué IDs va a cambiar? (factura + pagos conciliados)
        cr.execute("""
            WITH params AS (
                SELECT %s::int  AS inv_move_id,
                    %s::int  AS partner_id,
                    %s::int  AS acc_src_id
            ),
            inv_ml AS (
                /* Líneas CxC en la factura:
                - si viene acc_src -> por cuenta exacta
                - si NO viene acc_src -> por tipo CxC + partner (más tolerante)
                */
                SELECT aml.id
                FROM account_move_line aml
                JOIN account_account aa ON aa.id = aml.account_id
                JOIN params p ON TRUE
                WHERE aml.move_id = p.inv_move_id
                AND (
                        (p.acc_src_id IS NOT NULL AND aml.account_id = p.acc_src_id)
                    OR (p.acc_src_id IS NULL AND aa.account_type = 'asset_receivable' AND (aml.partner_id = p.partner_id OR p.partner_id IS NULL))
                )
            ),
            cp_ml AS (
                /* Contrapartes (pagos) conciliadas con esas líneas */
                SELECT DISTINCT aml2.id
                FROM inv_ml i
                JOIN account_partial_reconcile apr
                ON apr.debit_move_id = i.id OR apr.credit_move_id = i.id
                JOIN account_move_line aml2
                ON aml2.id = CASE WHEN apr.debit_move_id = i.id THEN apr.credit_move_id ELSE apr.debit_move_id END
                JOIN account_account aa2 ON aa2.id = aml2.account_id
                JOIN params p ON TRUE
                WHERE (
                        (p.acc_src_id IS NOT NULL AND aml2.account_id = p.acc_src_id)
                    OR (p.acc_src_id IS NULL AND aa2.account_type = 'asset_receivable' AND (aml2.partner_id = p.partner_id OR p.partner_id IS NULL))
                    )
            ),
            to_change AS (
                SELECT id FROM inv_ml
                UNION
                SELECT id FROM cp_ml
            )
            SELECT COALESCE(array_agg(id), '{}') FROM to_change
        """, (inv_move_id, partner_id, acc_src_id))

        ids_row = cr.fetchone()
        ids_to_change = ids_row[0] or []
        _logger.info("SQL CxC detectadas → %s líneas: %s", len(ids_to_change), ids_to_change)

        if not ids_to_change:
            # Dump de diagnóstico: ¿qué hay realmente en la factura?
            cr.execute("""
                SELECT aml.id, aa.code, aa.account_type, aml.debit, aml.credit, aml.partner_id
                FROM account_move_line aml
                JOIN account_account aa ON aa.id = aml.account_id
                WHERE aml.move_id = %s
                ORDER BY aml.id
            """, (inv_move_id,))
            dump = cr.fetchall()
            _logger.warning("Dump líneas de %s: %s", move.name, dump)
            raise UserError(f"No encontré líneas CxC para cambiar en {move.name} con la cuenta origen dada.")

        # 3) backup
        cr.execute("""
            INSERT INTO x_backup_move_line_account (move_line_id, old_account_id, new_account_id, note)
            SELECT aml.id, aml.account_id, %s, %s
            FROM account_move_line aml
            WHERE aml.id = ANY(%s)
        """, (acc_dst_id, note, ids_to_change))

        # 4) UPDATE
        cr.execute("""
            UPDATE account_move_line
            SET account_id = %s
            WHERE id = ANY(%s)
        """, (acc_dst_id, ids_to_change))

        # 5) resumen
        cr.execute("""
            SELECT COUNT(*) FROM x_backup_move_line_account WHERE note = %s
        """, (note,))
        changed = cr.fetchone()[0]
        _logger.info("SQL UPDATE OK → %s líneas cambiadas a %s en %s",
                    changed, getattr(acc_dst, "code", None), move.name)
        return {
            'effect': {
                'fadeout': 'slow',
                'message': f"✅ Reclasificación terminada: {changed} líneas actualizadas en {move.name}",
                'type': 'rainbow_man',
            }
        }

    def action_confirm_bulk(self):
        self.ensure_one()
        rec = self

        if not rec.account_dst_id:
            raise UserError("Selecciona la cuenta destino.")
        if rec.account_src_id and rec.account_src_id.id == rec.account_dst_id.id:
            raise UserError("La cuenta origen y destino no pueden ser la misma.")

        prefixes = [
            'FC',
            'DF',
            'STJ',
            'PBN',
            'RF',
            'PC',
            'FACT',
            'GT',
            'TD',
            'DS',
            'DSMG',
        ]

        # Buscamos en LÍNEAS, igual que la vista de "Apuntes contables"
        line_dom = [
            ('company_id', '=', rec.company_id.id),
            ('account_id', '=', rec.account_src_id.id),
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', 'in', ('out_invoice','out_refund','entry','in_invoice','in_refund')),
        ]
        if rec.journal_id:
            prefixes = [
              'FACTU',
              'RFACTU'
            ]
            line_dom += [
                ('move_id.journal_id', '=', rec.journal_id.id),
            ]
        # OR para nombres y para numéricos
        name_conds = [('move_id.name', 'ilike', f'{p}%') for p in prefixes]
        numeric_conds = [('move_id.name', 'ilike', f'{d}%') for d in range(10)]
        name_or = ['|'] * (len(name_conds) + len(numeric_conds) - 1) + name_conds + numeric_conds

        line_dom += name_or

        AML = self.env['account.move.line']
        lines = AML.search(line_dom)

        # Obtener asientos únicos
        move_ids = list({l.move_id.id for l in lines})
        moves = self.env['account.move'].browse(move_ids)

        if not moves:
            raise UserError("No se encontraron facturas que cumplan el filtro para reclasificar.")

        _logger.info("[BULK] %s facturas candidatas: %s", len(moves), moves.mapped('name'))

        # 2) Ejecutar una por una con savepoint (si una falla, seguimos con las demás)
        ok_count = 0
        fail = []   # [(move_name, error), ...]

        # Etiqueta de lote para rastrear en el backup (opcional)
        batch_tag = f"bulk-{fields.Datetime.now()}"
        _logger.info("[BULK] Iniciando lote %s (src=%s -> dst=%s)", batch_tag,
                    getattr(rec.account_src_id, 'code', None),
                    getattr(rec.account_dst_id, 'code', None))

        for move in moves:
            try:
                with self.env.cr.savepoint():  # aísla errores por factura
                    # Llamada a tu método SQL (tolera acc_src=None)
                    # Si quieres que el 'note' del backup incluya el batch, añade una variante del método con parámetro note_extra
                    self._reclass_update_invoice_sql(move, rec.account_src_id, rec.account_dst_id, rec.company_id)
                    ok_count += 1
            except Exception as e:
                # No interrumpe el resto
                fail.append((move.name, str(e)))
                _logger.exception("[BULK] Falló %s: %s", move.name, e)

        # 3) Resumen final
        msg = f"✅ Lote terminado. Exitosas: {ok_count} / Totales: {len(moves)}"
        if fail:
            # Muestra solo los primeros 5 errores para no saturar el toast
            primeros = ", ".join(f"{n}" for n, _ in fail[:5])
            msg += f". Fallidas: {len(fail)} (p.ej: {primeros})"
        _logger.info("[BULK] %s | Errores: %s", msg, len(fail))

        return {
            'effect': {
                'fadeout': 'slow',
                'message': msg,
                'type': 'rainbow_man',
            }
        }
