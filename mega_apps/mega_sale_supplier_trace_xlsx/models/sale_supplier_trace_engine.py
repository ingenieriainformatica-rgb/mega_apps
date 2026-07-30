# -*- coding: utf-8 -*-
"""Motor de atribucion de proveedor por venta.

No escribe en ningun modelo de Odoo. Solo lee account.move, account.move.line,
sale.order.line, stock.move, stock.move.line, stock.valuation.layer,
purchase.order.line y res.partner, y devuelve estructuras Python en memoria.

No consulta product.supplierinfo en ningun punto de este archivo.

Terminologia interna:
- "fila de atribucion" (attribution row): un dict con una cantidad ya repartida
  entre facturas/proveedores, nunca la cantidad completa de la linea.
- "exacto": solo lote/serie con recepcion+purchase_line_id demostrable, o
  cadena move_orig_ids/move_dest_ids ininterrumpida hasta un purchase_line_id.
- "probable": reconstruccion cronologica de consumo (replica de la logica de
  _run_fifo del nucleo) contra stock.valuation.layer. NUNCA se marca "exacto",
  aunque el producto tenga costeo FIFO (asi lo exige el diseno aprobado).
- "no_determinado": evidencia insuficiente. Nunca se asigna un proveedor por
  descarte (ni el primero, ni el mas reciente, ni por sequence).
"""
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare


STATUS_EXACT = 'exact'
STATUS_PROBABLE = 'probable'
STATUS_NOT_DETERMINED = 'not_determined'

METHOD_LABELS = {
    'lot_exact': 'Lote/serie trazado a recepcion con orden de compra',
    'chain_exact': 'Cadena directa de movimientos (MTO/Dropship)',
    'fifo_probable': 'Probable por FIFO cronologico',
    'credit_note_inherit': 'Heredado proporcionalmente de la factura original (nota credito)',
}

FIFO_WARNING = (
    "Los resultados clasificados como probables corresponden a una atribucion "
    "cronologica de inventario y no demuestran trazabilidad fisica exacta."
)


def _as_date(value):
    """Normaliza Date/Datetime a datetime.date para comparaciones cronologicas."""
    if not value:
        return None
    return value.date() if hasattr(value, 'date') else value


class SaleSupplierTraceEngine(models.AbstractModel):
    _name = 'sale.supplier.trace.engine'
    _description = 'Motor de atribucion de proveedor por venta (solo lectura)'

    # ------------------------------------------------------------------
    # Punto de entrada
    # ------------------------------------------------------------------

    @api.model
    def run(self, params):
        """params: dict validado por el wizard. Devuelve un dict con
        'move_lines' (recordset analizado), 'rows' (filas ya filtradas por
        proveedor si se pidio) y 'all_rows' (sin filtrar, para los totales
        de cobertura que deben reflejar TODO lo analizado)."""
        move_lines = self._search_invoice_lines(params)
        self._check_limit(move_lines)

        context = {
            'params': params,
            'reconcile_cache': {},   # sale_order_line.id -> {invoice_line.id: [(out_move|None, qty), ...]}
            'out_move_cache': {},    # stock_move.id -> [breakdown dict, ...]
            'fifo_cache': {},        # (product.id, company.id) -> {stock_move.id: [entry, ...]}
            'credit_cache': {},      # invoice_line.id -> [row, ...]  (memoiza lineas ya atribuidas, factura u origen de NC)
        }

        all_rows = []
        for line in move_lines:
            all_rows.extend(self._attribute_invoice_line(line, context))

        supplier_filter = params.get('supplier_id')
        if supplier_filter:
            rows = [r for r in all_rows if r.get('supplier') and r['supplier'].id == supplier_filter]
        else:
            rows = all_rows

        return {
            'move_lines': move_lines,
            'all_rows': all_rows,
            'rows': rows,
        }

    # ------------------------------------------------------------------
    # Busqueda inicial y limite de rendimiento (punto 17)
    # ------------------------------------------------------------------

    @api.model
    def _search_invoice_lines(self, params):
        move_types = {
            'out_invoice': ['out_invoice'],
            'out_refund': ['out_refund'],
            'both': ['out_invoice', 'out_refund'],
        }[params['doc_type']]

        domain = [
            ('move_id.move_type', 'in', move_types),
            ('move_id.state', '=', 'posted'),
            ('display_type', '=', 'product'),
            ('move_id.invoice_date', '>=', params['date_from']),
            ('move_id.invoice_date', '<=', params['date_to']),
            ('move_id.company_id', 'in', params['company_ids']),
        ]
        if not params.get('include_services'):
            # is_storable (no `type`) es el campo correcto en Odoo 18 para saber
            # si un producto tiene existencias fisicas rastreables (ver analisis previo).
            domain.append(('product_id.product_tmpl_id.is_storable', '=', True))
        if params.get('partner_id'):
            domain.append(('move_id.partner_id', '=', params['partner_id']))
        if params.get('product_id'):
            domain.append(('product_id', '=', params['product_id']))
        if params.get('product_categ_id'):
            domain.append(('product_id.categ_id', '=', params['product_categ_id']))
        if params.get('move_id'):
            domain.append(('move_id', '=', params['move_id']))
        if params.get('journal_id'):
            domain.append(('move_id.journal_id', '=', params['journal_id']))

        return self.env['account.move.line'].search(domain, order='invoice_date, move_id, id')

    @api.model
    def _check_limit(self, move_lines):
        limit = int(self.env['ir.config_parameter'].sudo().get_param(
            'mega_sale_supplier_trace_xlsx.max_lines', default='5000'))
        # sudo() aqui es exclusivamente para LEER un ir.config_parameter tecnico
        # (limite de rendimiento), nunca para sortear permisos sobre datos de negocio.
        if len(move_lines) > limit:
            raise UserError(
                "El rango solicitado contiene %s lineas de factura, por encima del "
                "limite configurado (%s). Reduzca el rango de fechas o los filtros, "
                "o aumente 'mega_sale_supplier_trace_xlsx.max_lines' en Parametros "
                "del Sistema si el volumen es intencional." % (len(move_lines), limit)
            )

    # ------------------------------------------------------------------
    # Despacho por linea de factura
    # ------------------------------------------------------------------

    def _attribute_invoice_line(self, line, context):
        cache = context['credit_cache']
        if line.id in cache:
            return cache[line.id]
        move = line.move_id
        if move.move_type == 'out_refund':
            rows = self._attribute_credit_note_line(line, context)
        else:
            rows = self._attribute_customer_invoice_line(line, context)
        cache[line.id] = rows
        return rows

    def _attribute_customer_invoice_line(self, line, context):
        if not line.product_id.product_tmpl_id.is_storable:
            return self._finalize_amounts(line, [self._raw_row(
                status=STATUS_NOT_DETERMINED,
                note='Servicio o producto no almacenable: no existe una unidad fisica que rastrear.',
            )])

        sale_lines = line.sale_line_ids
        if not sale_lines:
            return self._finalize_amounts(line, [self._raw_row(
                status=STATUS_NOT_DETERMINED,
                note='Factura manual sin linea de venta (sale.order.line) relacionada.',
            )])

        raw_rows = []
        for sale_line in sale_lines:
            reconciliation = self._get_or_reconcile_sale_line(sale_line, context)
            claims = reconciliation.get(line.id)
            if not claims:
                raw_rows.append(self._raw_row(
                    status=STATUS_NOT_DETERMINED, qty=line.quantity / len(sale_lines),
                    note='No hay entregas validadas (stock.move done) asociadas a esta linea de venta.',
                ))
                continue
            for out_move, qty in claims:
                if out_move is None:
                    raw_rows.append(self._raw_row(
                        status=STATUS_NOT_DETERMINED, qty=qty,
                        note='Facturado antes de la entrega fisica: no habia existencia entregada '
                             'disponible a la fecha de esta factura.',
                    ))
                    continue
                breakdown = self._get_or_resolve_out_move(out_move, context)
                move_total = sum(b['qty'] for b in breakdown) or 1.0
                for b in breakdown:
                    share_qty = qty * (b['qty'] / move_total)
                    if float_is_zero(share_qty, precision_rounding=line.product_uom_id.rounding or 0.01):
                        continue
                    raw_rows.append(self._raw_row(
                        status=b['status'], qty=share_qty, supplier=b.get('supplier'),
                        method=b.get('method'), note=b.get('note', ''),
                        purchase_order=b.get('purchase_order'), purchase_line=b.get('purchase_line'),
                        receipt_move=b.get('receipt_move'), delivery_move=out_move, lot_id=b.get('lot_id'),
                    ))
        return self._finalize_amounts(line, raw_rows)

    # ------------------------------------------------------------------
    # Notas credito (punto 7)
    # ------------------------------------------------------------------

    def _attribute_credit_note_line(self, line, context):
        original_line = self._find_original_line_for_credit(line)
        if original_line is None:
            return self._finalize_amounts(line, [self._raw_row(
                status=STATUS_NOT_DETERMINED,
                note='Nota credito sin factura original relacionada (reversed_entry_id ausente o linea no identificable).',
            )])

        original_rows = self._attribute_invoice_line(original_line, context)
        original_total_qty = sum(r['qty'] for r in original_rows) or original_line.quantity
        if float_is_zero(original_total_qty, precision_rounding=0.0001):
            return self._finalize_amounts(line, [self._raw_row(
                status=STATUS_NOT_DETERMINED,
                note='La factura original no tiene cantidad atribuible para prorratear la nota credito.',
            )])

        has_physical_return = self._has_physical_return_evidence(original_line, line)
        return_note = (' (con devolucion fisica evidenciada en inventario)' if has_physical_return
                        else ' (sin devolucion fisica evidenciada; reversion contable)')

        raw_rows = []
        for orow in original_rows:
            fraction = orow['qty'] / original_total_qty
            raw_rows.append(self._raw_row(
                status=orow['status'], qty=line.quantity * fraction, supplier=orow.get('supplier'),
                method=orow.get('method'),
                note=((orow.get('note') or '') + ' | ' + METHOD_LABELS['credit_note_inherit'] + return_note).strip(' |'),
                purchase_order=orow.get('purchase_order'), purchase_line=orow.get('purchase_line'),
                receipt_move=orow.get('receipt_move'), delivery_move=orow.get('delivery_move'),
                lot_id=orow.get('lot_id'),
            ))

        rows = self._finalize_amounts(line, raw_rows)
        # Convencion de signo de este reporte (no de la contabilidad de Odoo, que no se toca):
        # las notas credito se muestran en negativo para que sumen coherentemente con las facturas.
        for r in rows:
            r['qty'] *= -1
            r['subtotal'] *= -1
            r['tax'] *= -1
            r['total'] *= -1
        return rows

    def _find_original_line_for_credit(self, line):
        move = line.move_id
        original_move = move.reversed_entry_id
        if not original_move or original_move.state != 'posted':
            return None
        candidates = original_move.invoice_line_ids.filtered(
            lambda l: l.display_type == 'product' and l.product_id == line.product_id)
        if not candidates:
            return None
        if line.sale_line_ids:
            matched = candidates.filtered(lambda l: l.sale_line_ids & line.sale_line_ids)
            if matched:
                candidates = matched
        return candidates[:1]

    def _has_physical_return_evidence(self, original_line, credit_line):
        original_out_moves = original_line.sale_line_ids.mapped('move_ids').filtered(
            lambda m: m.state == 'done' and m.location_dest_id.usage == 'customer')
        if not original_out_moves:
            return False
        return bool(self.env['stock.move'].search_count([
            ('origin_returned_move_id', 'in', original_out_moves.ids),
            ('state', '=', 'done'),
        ]))

    # ------------------------------------------------------------------
    # Etapa 1: conciliacion entrega <-> factura por sale.order.line (punto 6)
    # ------------------------------------------------------------------

    def _get_or_reconcile_sale_line(self, sale_line, context):
        cache = context['reconcile_cache']
        if sale_line.id in cache:
            return cache[sale_line.id]
        result = self._reconcile_sale_line(sale_line)
        cache[sale_line.id] = result
        return result

    def _reconcile_sale_line(self, sale_line):
        out_moves = sale_line.move_ids.filtered(
            lambda m: m.state == 'done' and m.location_dest_id.usage == 'customer')
        out_moves = out_moves.sorted(key=lambda m: (_as_date(m.date) or fields.Date.today(), m.id))
        pool = [{'move': m, 'remaining': m.quantity} for m in out_moves]

        inv_lines = sale_line.invoice_lines.filtered(
            lambda l: l.move_id.state == 'posted' and l.move_id.move_type == 'out_invoice')
        inv_lines = inv_lines.sorted(
            key=lambda l: (_as_date(l.move_id.invoice_date or l.move_id.date), l.move_id.id, l.id))

        result = {}
        for inv_line in inv_lines:
            invoice_date = _as_date(inv_line.move_id.invoice_date or inv_line.move_id.date)
            need = inv_line.product_uom_id._compute_quantity(inv_line.quantity, sale_line.product_uom)
            claims = []
            for slot in pool:
                if float_is_zero(need, precision_rounding=sale_line.product_uom.rounding or 0.01):
                    break
                if slot['remaining'] <= 0:
                    continue
                move_date = _as_date(slot['move'].date)
                if move_date and invoice_date and move_date > invoice_date:
                    continue  # esta entrega ocurrio (cronologicamente) despues de esta factura
                take = min(need, slot['remaining'])
                if take <= 0:
                    continue
                slot['remaining'] -= take
                claims.append((slot['move'], take))
                need -= take
            if need > 0 and not float_is_zero(need, precision_rounding=sale_line.product_uom.rounding or 0.01):
                claims.append((None, need))
            result[inv_line.id] = claims
        return result

    # ------------------------------------------------------------------
    # Etapa 2: out_move -> desglose de proveedor
    # ------------------------------------------------------------------

    def _get_or_resolve_out_move(self, move, context):
        cache = context['out_move_cache']
        if move.id in cache:
            return cache[move.id]
        breakdown = self._resolve_out_move(move, context)
        cache[move.id] = breakdown
        return breakdown

    def _resolve_out_move(self, move, context):
        total_qty = move.quantity
        if float_is_zero(total_qty, precision_rounding=move.product_uom.rounding or 0.01):
            return []
        remaining = total_qty
        breakdown = []

        # (a) Lote/serie exacto (punto 4)
        if move.product_id.tracking != 'none' and move.move_line_ids:
            for ml in move.move_line_ids.filtered('lot_id'):
                qty = ml.product_uom_id._compute_quantity(ml.quantity, move.product_id.uom_id)
                if float_is_zero(qty, precision_rounding=move.product_uom.rounding or 0.01):
                    continue
                for res in self._resolve_lot_exact(move.product_id, ml.lot_id, qty):
                    breakdown.append(res)
                    remaining -= res['qty']

        # (b) Cadena directa MTO/Dropship (punto 5)
        if remaining > 0 and not float_is_zero(remaining, precision_rounding=move.product_uom.rounding or 0.01):
            chain_rows = self._resolve_move_chain_exact(move, remaining)
            for res in chain_rows:
                breakdown.append(res)
                remaining -= res['qty']

        # (c) Reconstruccion cronologica FIFO -> siempre "probable" (punto 2 y 3)
        if remaining > 0 and not float_is_zero(remaining, precision_rounding=move.product_uom.rounding or 0.01):
            breakdown.extend(self._resolve_fifo_probable(move, context))

        return breakdown

    def _resolve_lot_exact(self, product, lot, qty_needed):
        """Exacto solo si la MISMA lot/serie de salida coincide con una
        recepcion cuyo movimiento tiene purchase_line_id (punto 4)."""
        incoming_lines = self.env['stock.move.line'].search([
            ('lot_id', '=', lot.id),
            ('product_id', '=', product.id),
            ('state', '=', 'done'),
            ('move_id.purchase_line_id', '!=', False),
            ('location_dest_id.usage', '=', 'internal'),
        ], order='date, id')
        rows = []
        remaining_needed = qty_needed
        for ml in incoming_lines:
            if remaining_needed <= 0:
                break
            available = ml.product_uom_id._compute_quantity(ml.quantity, product.uom_id)
            take = min(remaining_needed, available)
            if take <= 0:
                continue
            po_line = ml.move_id.purchase_line_id
            rows.append(self._breakdown_row(
                status=STATUS_EXACT, qty=take, supplier=po_line.order_id.partner_id,
                method=METHOD_LABELS['lot_exact'], purchase_order=po_line.order_id,
                purchase_line=po_line, receipt_move=ml.move_id, lot_id=lot,
            ))
            remaining_needed -= take
        if remaining_needed > 0:
            rows.append(self._breakdown_row(
                status=STATUS_NOT_DETERMINED, qty=remaining_needed,
                note='Lote/serie sin recepcion de compra demostrable (posible apertura, ajuste o produccion).',
            ))
        return rows

    def _resolve_move_chain_exact(self, move, qty_needed):
        """Solo exacto si la cadena move_orig_ids es unica (sin ramificar) y
        termina en una recepcion con purchase_line_id (punto 5)."""
        current = move.move_orig_ids
        visited = set()
        while current:
            if len(current) != 1 or current.id in visited:
                return []  # cadena ambigua o ciclica: no es demostrable como exacta
            visited.add(current.id)
            if current.purchase_line_id:
                po_line = current.purchase_line_id
                available = current.product_uom._compute_quantity(current.quantity, move.product_id.uom_id)
                qty = min(qty_needed, available)
                if qty <= 0:
                    return []
                return [self._breakdown_row(
                    status=STATUS_EXACT, qty=qty, supplier=po_line.order_id.partner_id,
                    method=METHOD_LABELS['chain_exact'], purchase_order=po_line.order_id,
                    purchase_line=po_line, receipt_move=current,
                )]
            current = current.move_orig_ids
        return []

    # ------------------------------------------------------------------
    # Reconstruccion cronologica FIFO (puntos 2, 3, 8) -- SIEMPRE "probable"
    # ------------------------------------------------------------------

    def _resolve_fifo_probable(self, move, context):
        consumption = self._get_or_build_fifo_replay(move.product_id, move.company_id, context)
        entries = consumption.get(move.id)
        if not entries:
            return [self._breakdown_row(
                status=STATUS_NOT_DETERMINED, qty=move.quantity,
                note='Sin capas de valoracion (stock.valuation.layer) para reconstruir el consumo de este producto.',
            )]
        rows = []
        for entry in entries:
            cand = entry['candidate']
            qty = entry['qty']
            if cand is None:
                rows.append(self._breakdown_row(
                    status=STATUS_NOT_DETERMINED, qty=qty,
                    note='Inventario insuficiente en el momento de la venta (posible faltante o desfase de valoracion).',
                ))
            elif cand['purchase_line']:
                rows.append(self._breakdown_row(
                    status=STATUS_PROBABLE, qty=qty, supplier=cand['supplier'],
                    method=METHOD_LABELS['fifo_probable'], purchase_order=cand['purchase_line'].order_id,
                    purchase_line=cand['purchase_line'], receipt_move=cand['move'],
                ))
            else:
                rows.append(self._breakdown_row(
                    status=STATUS_NOT_DETERMINED, qty=qty,
                    note='La capa consumida no proviene de una orden de compra (ajuste de inventario, '
                         'transferencia interna, devolucion de cliente reingresada u otro movimiento sin '
                         'purchase_line_id). No se asigna proveedor.',
                ))
        return rows

    def _get_or_build_fifo_replay(self, product, company, context):
        key = (product.id, company.id)
        cache = context['fifo_cache']
        if key in cache:
            return cache[key]
        cache[key] = self._build_fifo_replay(product, company)
        return cache[key]

    def _build_fifo_replay(self, product, company):
        """Reproduce cronologicamente TODO el historial de stock.valuation.layer
        del producto (no solo desde date_from: el balance disponible antes del
        rango depende de toda la historia previa, punto 2). No modifica
        remaining_qty ni ninguna capa; es una simulacion en memoria.

        El alcance se acota por PRODUCTO (solo se construye para productos que
        realmente aparecen en las lineas analizadas, y se cachea una sola vez
        por producto+compania para toda la ejecucion), no por ventana de tiempo,
        porque truncar el tiempo rompe el orden FIFO real.
        """
        layers = self.env['stock.valuation.layer'].search([
            ('product_id', '=', product.id),
            ('company_id', '=', company.id),
        ], order='create_date, id')

        queue = []
        consumption_by_move = defaultdict(list)
        rounding = product.uom_id.rounding or 0.01

        for svl in layers:
            move = svl.stock_move_id
            if float_compare(svl.quantity, 0, precision_rounding=rounding) > 0:
                po_line = move.purchase_line_id if move else False
                queue.append({
                    'remaining': svl.quantity,
                    'purchase_line': po_line,
                    'supplier': po_line.order_id.partner_id if po_line else False,
                    'move': move,
                })
            elif float_compare(svl.quantity, 0, precision_rounding=rounding) < 0:
                need = -svl.quantity
                consumed = []
                for cand in queue:
                    if float_is_zero(need, precision_rounding=rounding):
                        break
                    if cand['remaining'] <= 0:
                        continue
                    take = min(need, cand['remaining'])
                    cand['remaining'] -= take
                    need -= take
                    consumed.append({'candidate': cand, 'qty': take})
                if need > 0 and not float_is_zero(need, precision_rounding=rounding):
                    consumed.append({'candidate': None, 'qty': need})
                if move:
                    consumption_by_move[move.id] = consumed
            # svl.quantity == 0 (landed costs, revaluaciones manuales): no son
            # candidatos de entrada ni eventos de salida, se ignoran correctamente.

        return consumption_by_move

    # ------------------------------------------------------------------
    # Construccion de filas y montos (puntos 9, 10, 11)
    # ------------------------------------------------------------------

    @staticmethod
    def _raw_row(status, qty=0.0, supplier=None, method=None, note='', purchase_order=None,
                 purchase_line=None, receipt_move=None, delivery_move=None, lot_id=None):
        return {
            'status': status, 'qty': qty, 'supplier': supplier, 'method': method or '', 'note': note or '',
            'purchase_order': purchase_order, 'purchase_line': purchase_line,
            'receipt_move': receipt_move, 'delivery_move': delivery_move, 'lot_id': lot_id,
        }

    _breakdown_row = _raw_row  # mismo shape, usado en la Etapa 2 (sin delivery_move propio)

    def _finalize_amounts(self, line, raw_rows):
        """Prorratea subtotal/impuesto/total de la LINEA (ya calculados por la
        contabilidad, nunca reconstruidos desde tax_ids, punto 11) segun la
        fraccion de cantidad de cada fila. El residuo de redondeo se aplica
        SOLO a la ultima fila de esta misma linea (punto 10)."""
        if not raw_rows:
            return []
        total_qty = line.quantity
        currency = line.currency_id or line.move_id.currency_id
        subtotal = line.price_subtotal
        total = line.price_total
        tax = total - subtotal

        rows_qty_sum = sum(r['qty'] for r in raw_rows)
        # Normaliza para que la suma de qty de las filas sea exactamente line.quantity,
        # sin perder la proporcion relativa ya calculada (evita arrastre de error de UoM).
        scale = (total_qty / rows_qty_sum) if rows_qty_sum else 0.0

        n = len(raw_rows)
        acc_sub = acc_tax = acc_tot = 0.0
        out_rows = []
        for i, r in enumerate(raw_rows):
            qty = r['qty'] * scale
            fraction = (qty / total_qty) if total_qty else 0.0
            if i < n - 1:
                r_sub = currency.round(subtotal * fraction)
                r_tax = currency.round(tax * fraction)
                r_tot = currency.round(total * fraction)
                acc_sub += r_sub
                acc_tax += r_tax
                acc_tot += r_tot
            else:
                r_sub = currency.round(subtotal - acc_sub)
                r_tax = currency.round(tax - acc_tax)
                r_tot = currency.round(total - acc_tot)
            out_rows.append({
                'invoice_line': line, 'move': line.move_id, 'status': r['status'],
                'qty': qty, 'uom': line.product_uom_id, 'supplier': r.get('supplier'),
                'method': r.get('method', ''), 'note': r.get('note', ''),
                'purchase_order': r.get('purchase_order'), 'purchase_line': r.get('purchase_line'),
                'receipt_move': r.get('receipt_move'), 'delivery_move': r.get('delivery_move'),
                'lot_id': r.get('lot_id'),
                'subtotal': r_sub, 'tax': r_tax, 'total': r_tot, 'currency': currency,
            })
        return out_rows
