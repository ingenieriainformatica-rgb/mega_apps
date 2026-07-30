# -*- coding: utf-8 -*-
"""Construccion del libro XLSX de trazabilidad de proveedor por venta.

Solo lee la estructura de resultados ya calculada por sale.supplier.trace.engine
(diccionarios en memoria); no vuelve a consultar el ORM salvo para formatear
nombres/etiquetas ya disponibles en los recordsets de las filas.
"""
import io
from datetime import datetime

from odoo import models
from odoo.tools.misc import xlsxwriter

from ..models.sale_supplier_trace_engine import STATUS_EXACT, STATUS_PROBABLE, STATUS_NOT_DETERMINED, FIFO_WARNING

STATUS_LABELS = {
    STATUS_EXACT: 'Exacto',
    STATUS_PROBABLE: 'Probable',
    STATUS_NOT_DETERMINED: 'No determinado',
}
DOC_TYPE_LABELS = {
    'out_invoice': 'Factura de cliente',
    'out_refund': 'Nota credito',
}

DETAIL_HEADERS = [
    'Factura', 'Tipo de documento', 'Fecha de factura', 'Cliente', 'NIT/Documento del cliente',
    'Vehiculo', 'Descripcion',
    'Vendedor/Asesor', 'Producto', 'Referencia interna', 'Categoria',
    'Cantidad facturada', 'Cantidad atribuida', 'Unidad de medida',
    'Proveedor', 'NIT del proveedor', 'Orden de compra', 'Factura de proveedor',
    'Fecha de compra', 'Recepcion', 'Entrega',
    'Subtotal atribuido', 'Impuesto atribuido', 'Total atribuido',
    'Estado', 'Metodo de determinacion', 'Observacion',
]


class SaleSupplierTraceXlsxBuilder(models.AbstractModel):
    _name = 'sale.supplier.trace.xlsx.builder'
    _description = 'Constructor del archivo XLSX de trazabilidad de proveedor'

    def build(self, wizard, result):
        rows = result['rows']
        move_lines = result['move_lines']

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        formats = self._make_formats(workbook)

        self._build_detail_sheet(workbook, formats, rows)
        self._build_summary_sheet(workbook, formats, rows)
        self._build_not_determined_sheet(workbook, formats, rows)
        self._build_params_sheet(workbook, formats, wizard, move_lines, rows)

        workbook.close()
        return output.getvalue()

    # ------------------------------------------------------------------

    def _make_formats(self, workbook):
        return {
            'header': workbook.add_format({
                'bold': True, 'bg_color': '#1F4E5F', 'font_color': 'white',
                'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
            }),
            'title': workbook.add_format({'bold': True, 'font_size': 14}),
            'subtitle': workbook.add_format({'italic': True, 'font_color': '#666666'}),
            'money': workbook.add_format({'num_format': '#,##0.00'}),
            'money_bold': workbook.add_format({'num_format': '#,##0.00', 'bold': True, 'top': 1}),
            'qty': workbook.add_format({'num_format': '#,##0.0000'}),
            'qty_bold': workbook.add_format({'num_format': '#,##0.0000', 'bold': True, 'top': 1}),
            'date': workbook.add_format({'num_format': 'yyyy-mm-dd'}),
            'pct': workbook.add_format({'num_format': '0.00%'}),
            'bold': workbook.add_format({'bold': True}),
            'wrap': workbook.add_format({'text_wrap': True, 'valign': 'top'}),
            'status_exact': workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'}),
            'status_probable': workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500'}),
            'status_not_determined': workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'}),
        }

    def _status_format(self, formats, status):
        return {
            STATUS_EXACT: formats['status_exact'],
            STATUS_PROBABLE: formats['status_probable'],
            STATUS_NOT_DETERMINED: formats['status_not_determined'],
        }[status]

    # ------------------------------------------------------------------

    def _write_detail_row(self, sheet, fmts, row_idx, row):
        move = row['move']
        line = row['invoice_line']
        product = line.product_id
        supplier = row.get('supplier')
        po = row.get('purchase_order')
        po_line = row.get('purchase_line')
        receipt = row.get('receipt_move')
        delivery = row.get('delivery_move')

        vendor_bill_name = ''
        purchase_date = None
        if po:
            bills = po.invoice_ids.filtered(lambda b: b.state == 'posted')
            if bills:
                vendor_bill_name = ', '.join(bills.mapped('name'))
            purchase_date = po.date_approve or po.date_order

        status_fmt = self._status_format(fmts, row['status'])

        values = [
            move.name or move.ref or '/',
            DOC_TYPE_LABELS.get(move.move_type, move.move_type),
            move.invoice_date,
            move.partner_id.display_name,
            move.partner_id.vat or '',
            getattr(move, 'vehicle', '') or '',
            getattr(move, 'x_studio_descripcin_1', '') or '',
            move.invoice_user_id.name or '',
            product.display_name,
            product.default_code or '',
            product.categ_id.display_name or '',
            line.quantity,
            row['qty'],
            row['uom'].name,
            supplier.display_name if supplier else '',
            supplier.vat if supplier else '',
            po.name if po else '',
            vendor_bill_name,
            purchase_date,
            receipt.reference or receipt.name if receipt else '',
            delivery.reference or delivery.name if delivery else '',
            row['subtotal'],
            row['tax'],
            row['total'],
            STATUS_LABELS[row['status']],
            row.get('method') or '',
            row.get('note') or '',
        ]
        col_formats = {2: fmts['date'], 11: fmts['qty'], 12: fmts['qty'], 18: fmts['date'],
                        21: fmts['money'], 22: fmts['money'], 23: fmts['money']}
        for col, value in enumerate(values):
            fmt = col_formats.get(col)
            if col == 24:  # Estado
                sheet.write(row_idx, col, value, status_fmt)
            elif fmt is not None and value:
                sheet.write(row_idx, col, value, fmt)
            else:
                sheet.write(row_idx, col, value or '')

    def _build_detail_sheet(self, workbook, fmts, rows):
        sheet = workbook.add_worksheet('Detalle')
        for col, header in enumerate(DETAIL_HEADERS):
            sheet.write(0, col, header, fmts['header'])
        sheet.freeze_panes(1, 0)

        row_idx = 1
        for row in rows:
            self._write_detail_row(sheet, fmts, row_idx, row)
            row_idx += 1

        if rows:
            sheet.autofilter(0, 0, row_idx - 1, len(DETAIL_HEADERS) - 1)
            sheet.write(row_idx, 11, 'TOTAL', fmts['bold'])
            sheet.write_formula(row_idx, 12, '=SUM(M2:M%d)' % row_idx, fmts['qty_bold'])
            sheet.write_formula(row_idx, 21, '=SUM(V2:V%d)' % row_idx, fmts['money_bold'])
            sheet.write_formula(row_idx, 22, '=SUM(W2:W%d)' % row_idx, fmts['money_bold'])
            sheet.write_formula(row_idx, 23, '=SUM(X2:X%d)' % row_idx, fmts['money_bold'])

        widths = [14, 16, 12, 26, 16, 16, 30, 18, 30, 14, 18, 12, 12, 10, 26, 16, 14, 16, 12, 14, 14, 14, 14, 14, 14, 30, 34]
        for col, width in enumerate(widths):
            sheet.set_column(col, col, width)

    # ------------------------------------------------------------------

    def _build_summary_sheet(self, workbook, fmts, rows):
        sheet = workbook.add_worksheet('Resumen por proveedor')
        headers = ['Proveedor', 'NIT', 'Estado predominante', 'Cantidad atribuida',
                   'Subtotal atribuido', 'Impuesto atribuido', 'Total atribuido', 'Filas']
        for col, header in enumerate(headers):
            sheet.write(0, col, header, fmts['header'])
        sheet.freeze_panes(1, 0)

        buckets = {}
        for row in rows:
            supplier = row.get('supplier')
            key = supplier.id if supplier else 'not_determined'
            bucket = buckets.setdefault(key, {
                'name': supplier.display_name if supplier else 'No determinado',
                'vat': supplier.vat if supplier else '',
                'statuses': {}, 'qty': 0.0, 'subtotal': 0.0, 'tax': 0.0, 'total': 0.0, 'count': 0,
            })
            bucket['qty'] += row['qty']
            bucket['subtotal'] += row['subtotal']
            bucket['tax'] += row['tax']
            bucket['total'] += row['total']
            bucket['count'] += 1
            bucket['statuses'][row['status']] = bucket['statuses'].get(row['status'], 0) + row['qty']

        # Ordena por total atribuido descendente; "No determinado" siempre al final.
        ordered = sorted(
            (b for b in buckets.values() if b['name'] != 'No determinado'),
            key=lambda b: b['total'], reverse=True)
        if 'not_determined' in buckets:
            ordered.append(buckets['not_determined'])

        row_idx = 1
        for bucket in ordered:
            predominant = max(bucket['statuses'], key=bucket['statuses'].get) if bucket['statuses'] else ''
            sheet.write(row_idx, 0, bucket['name'])
            sheet.write(row_idx, 1, bucket['vat'] or '')
            sheet.write(row_idx, 2, STATUS_LABELS.get(predominant, ''))
            sheet.write(row_idx, 3, bucket['qty'], fmts['qty'])
            sheet.write(row_idx, 4, bucket['subtotal'], fmts['money'])
            sheet.write(row_idx, 5, bucket['tax'], fmts['money'])
            sheet.write(row_idx, 6, bucket['total'], fmts['money'])
            sheet.write(row_idx, 7, bucket['count'])
            row_idx += 1

        if ordered:
            sheet.write(row_idx, 0, 'TOTAL (suma de cantidades e importes ya atribuidos, sin duplicar ventas)',
                        fmts['bold'])
            sheet.write_formula(row_idx, 3, '=SUM(D2:D%d)' % row_idx, fmts['qty_bold'])
            sheet.write_formula(row_idx, 4, '=SUM(E2:E%d)' % row_idx, fmts['money_bold'])
            sheet.write_formula(row_idx, 5, '=SUM(F2:F%d)' % row_idx, fmts['money_bold'])
            sheet.write_formula(row_idx, 6, '=SUM(G2:G%d)' % row_idx, fmts['money_bold'])

        for col, width in enumerate([28, 16, 18, 16, 16, 16, 16, 8]):
            sheet.set_column(col, col, width)

    # ------------------------------------------------------------------

    def _build_not_determined_sheet(self, workbook, fmts, rows):
        sheet = workbook.add_worksheet('No determinados')
        headers = ['Factura', 'Fecha', 'Cliente', 'Producto', 'Cantidad no determinada',
                    'Unidad', 'Subtotal', 'Observacion (motivo)']
        for col, header in enumerate(headers):
            sheet.write(0, col, header, fmts['header'])
        sheet.freeze_panes(1, 0)

        nd_rows = [r for r in rows if r['status'] == STATUS_NOT_DETERMINED]
        row_idx = 1
        for row in nd_rows:
            move = row['move']
            line = row['invoice_line']
            sheet.write(row_idx, 0, move.name or move.ref or '/')
            sheet.write(row_idx, 1, move.invoice_date, fmts['date'])
            sheet.write(row_idx, 2, move.partner_id.display_name)
            sheet.write(row_idx, 3, line.product_id.display_name)
            sheet.write(row_idx, 4, row['qty'], fmts['qty'])
            sheet.write(row_idx, 5, row['uom'].name)
            sheet.write(row_idx, 6, row['subtotal'], fmts['money'])
            sheet.write(row_idx, 7, row.get('note') or '', fmts['wrap'])
            row_idx += 1

        if nd_rows:
            sheet.autofilter(0, 0, row_idx - 1, len(headers) - 1)
        for col, width in enumerate([14, 12, 26, 30, 16, 10, 14, 50]):
            sheet.set_column(col, col, width)

    # ------------------------------------------------------------------

    def _build_params_sheet(self, workbook, fmts, wizard, move_lines, rows):
        sheet = workbook.add_worksheet('Parametros y advertencias')
        sheet.write(0, 0, 'Trazabilidad de proveedor por venta', fmts['title'])
        sheet.write(1, 0, 'Generado: %s' % datetime.now().strftime('%Y-%m-%d %H:%M:%S'), fmts['subtitle'])

        params = [
            ('Rango de fechas', '%s a %s' % (wizard.date_from, wizard.date_to)),
            ('Cliente', wizard.partner_id.display_name if wizard.partner_id else '(todos)'),
            ('Producto', wizard.product_id.display_name if wizard.product_id else '(todos)'),
            ('Categoria de producto', wizard.product_categ_id.display_name if wizard.product_categ_id else '(todas)'),
            ('Factura', wizard.move_id.display_name if wizard.move_id else '(todas)'),
            ('Proveedor (filtro posterior a la atribucion)',
             wizard.supplier_id.display_name if wizard.supplier_id else '(todos)'),
            ('Diario', wizard.journal_id.display_name if wizard.journal_id else '(todos)'),
            ('Tipo de documento', dict(wizard._fields['doc_type'].selection)[wizard.doc_type]),
            ('Estado de trazabilidad',
             dict(wizard._fields['traceability_status_filter'].selection)[wizard.traceability_status_filter]),
            ('Incluir servicios', 'Si' if wizard.include_services else 'No'),
            ('Companias', ', '.join(wizard.company_ids.mapped('name'))),
            ('Lineas de factura analizadas', len(move_lines)),
            ('Documentos encontrados', len(move_lines.mapped('move_id'))),
            ('Filas de atribucion en este archivo', len(rows)),
        ]
        r = 3
        for label, value in params:
            sheet.write(r, 0, label, fmts['bold'])
            sheet.write(r, 1, value)
            r += 1

        r += 1
        sheet.write(r, 0, 'Advertencias', fmts['bold'])
        r += 1
        sheet.write(r, 0, FIFO_WARNING, fmts['wrap'])
        r += 1
        sheet.write(r, 0,
                     'El proveedor "Exacto" solo se asigna con evidencia directa (lote/serie o cadena '
                     'logistica completa). "Probable" es una atribucion cronologica de inventario, no una '
                     'demostracion fisica. "No determinado" significa evidencia insuficiente; nunca se '
                     'asigna un proveedor por descarte (ni el primero, ni el mas reciente, ni por sequence). '
                     'Este reporte no utiliza product.supplierinfo en ningun punto de su calculo.',
                     fmts['wrap'])
        sheet.set_column(0, 0, 42)
        sheet.set_column(1, 1, 50)
