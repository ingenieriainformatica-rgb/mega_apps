# -*- coding: utf-8 -*-
import base64
import io
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

from ..models.sale_supplier_trace_engine import (
    STATUS_EXACT, STATUS_PROBABLE, STATUS_NOT_DETERMINED, FIFO_WARNING,
)

EXPORT_GROUP = 'mega_sale_supplier_trace_xlsx.group_sale_supplier_trace_export'


class SaleSupplierTraceWizard(models.TransientModel):
    _name = 'sale.supplier.trace.wizard'
    _description = 'Trazabilidad de proveedor por venta'

    date_from = fields.Date(required=True, default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(required=True, default=fields.Date.today)

    partner_id = fields.Many2one('res.partner', string='Cliente')
    product_id = fields.Many2one('product.product', string='Producto')
    product_categ_id = fields.Many2one('product.category', string='Categoria de producto')
    move_id = fields.Many2one(
        'account.move', string='Factura',
        domain="[('move_type', 'in', ['out_invoice', 'out_refund']), ('state', '=', 'posted')]")
    supplier_id = fields.Many2one(
        'res.partner', string='Proveedor',
        help='Se aplica DESPUES de calcular la atribucion: filtra las filas ya '
             'resueltas cuyo proveedor coincide. No forma parte de la busqueda '
             'inicial de account.move.line (esta no se filtra por proveedor).')
    journal_id = fields.Many2one('account.journal', string='Diario', domain="[('type', '=', 'sale')]")

    doc_type = fields.Selection([
        ('out_invoice', 'Facturas de cliente'),
        ('out_refund', 'Notas credito'),
        ('both', 'Facturas y notas credito'),
    ], string='Tipo de documento', required=True, default='both')

    traceability_status_filter = fields.Selection([
        ('all', 'Todos'),
        ('exact', 'Exacto'),
        ('probable', 'Probable'),
        ('not_determined', 'No determinado'),
    ], string='Estado de trazabilidad', required=True, default='all')

    include_services = fields.Boolean(string='Incluir servicios', default=False)

    company_ids = fields.Many2many(
        'res.company', string='Companias',
        default=lambda self: self.env.companies,
        domain=lambda self: [('id', 'in', self.env.companies.ids)])

    # ---- resultado de "Vista previa" (solo lectura, calculado en memoria) ----
    preview_done = fields.Boolean(default=False)
    preview_documents = fields.Integer(string='Documentos encontrados', readonly=True)
    preview_lines = fields.Integer(string='Lineas de factura analizadas', readonly=True)
    preview_rows = fields.Integer(string='Filas de atribucion resultantes', readonly=True)
    preview_qty_exact = fields.Float(string='Cantidad exacta', readonly=True)
    preview_qty_probable = fields.Float(string='Cantidad probable', readonly=True)
    preview_qty_not_determined = fields.Float(string='Cantidad no determinada', readonly=True)
    preview_pct_exact = fields.Float(string='% exacto', readonly=True)
    preview_pct_probable = fields.Float(string='% probable', readonly=True)
    preview_pct_not_determined = fields.Float(string='% no determinado', readonly=True)
    preview_total_original = fields.Monetary(string='Total ventas del rango', readonly=True,
                                              currency_field='preview_currency_id')
    preview_total_attributed = fields.Monetary(string='Total atribuido (segun filtros)', readonly=True,
                                                currency_field='preview_currency_id')
    preview_difference = fields.Monetary(string='Diferencia', readonly=True,
                                          currency_field='preview_currency_id')
    preview_currency_id = fields.Many2one('res.currency', readonly=True,
                                           default=lambda self: self.env.company.currency_id)
    preview_warning = fields.Text(string='Advertencias', readonly=True)

    xlsx_file = fields.Binary(string='Archivo Excel', readonly=True, attachment=False)
    xlsx_filename = fields.Char(readonly=True)

    # ------------------------------------------------------------------
    # Parametros / validacion
    # ------------------------------------------------------------------

    def _get_params(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_('La fecha inicial no puede ser posterior a la fecha final.'))
        if not self.company_ids:
            raise UserError(_('Seleccione al menos una compania.'))
        return {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'partner_id': self.partner_id.id or None,
            'product_id': self.product_id.id or None,
            'product_categ_id': self.product_categ_id.id or None,
            'move_id': self.move_id.id or None,
            'supplier_id': self.supplier_id.id or None,
            'journal_id': self.journal_id.id or None,
            'doc_type': self.doc_type,
            'include_services': self.include_services,
            'company_ids': self.company_ids.ids,
        }

    def _run_engine(self):
        params = self._get_params()
        engine = self.env['sale.supplier.trace.engine']
        result = engine.run(params)
        status_filter = self.traceability_status_filter
        if status_filter != 'all':
            result['rows'] = [r for r in result['rows'] if r['status'] == status_filter]
        return result

    # ------------------------------------------------------------------
    # Vista previa
    # ------------------------------------------------------------------

    def action_preview(self):
        self.ensure_one()
        if not self.env.user.has_group('mega_sale_supplier_trace_xlsx.group_sale_supplier_trace_user'):
            raise AccessError(_('No tiene permiso para consultar la trazabilidad de proveedor.'))

        result = self._run_engine()
        move_lines = result['move_lines']
        rows = result['rows']

        qty_exact = sum(r['qty'] for r in rows if r['status'] == STATUS_EXACT)
        qty_probable = sum(r['qty'] for r in rows if r['status'] == STATUS_PROBABLE)
        qty_not_determined = sum(r['qty'] for r in rows if r['status'] == STATUS_NOT_DETERMINED)
        qty_total = qty_exact + qty_probable + qty_not_determined or 1.0

        total_original = sum(move_lines.mapped('price_total'))
        total_attributed = sum(r['total'] for r in rows)

        warnings = [FIFO_WARNING]
        limit = int(self.env['ir.config_parameter'].sudo().get_param(
            'mega_sale_supplier_trace_xlsx.max_lines', default='5000'))
        if len(move_lines) >= limit:
            warnings.append(
                'El rango analizado esta en el limite configurado (%s lineas). '
                'Si el volumen real es mayor, algunos resultados podrian no reflejarse; '
                'reduzca el rango o aumente el limite.' % limit)
        if self.supplier_id:
            warnings.append(
                'Filtro de proveedor activo: los totales de esta vista previa corresponden '
                'unicamente a las filas atribuidas a "%s", no al total de ventas del rango.'
                % self.supplier_id.display_name)

        self.write({
            'preview_done': True,
            'preview_documents': len(move_lines.mapped('move_id')),
            'preview_lines': len(move_lines),
            'preview_rows': len(rows),
            'preview_qty_exact': qty_exact,
            'preview_qty_probable': qty_probable,
            'preview_qty_not_determined': qty_not_determined,
            'preview_pct_exact': 100.0 * qty_exact / qty_total,
            'preview_pct_probable': 100.0 * qty_probable / qty_total,
            'preview_pct_not_determined': 100.0 * qty_not_determined / qty_total,
            'preview_total_original': total_original,
            'preview_total_attributed': total_attributed,
            'preview_difference': total_original - total_attributed,
            'preview_currency_id': (move_lines[:1].currency_id or self.env.company.currency_id).id,
            'preview_warning': '\n'.join(warnings),
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ------------------------------------------------------------------
    # Descarga XLSX
    # ------------------------------------------------------------------

    def action_generate_xlsx(self):
        self.ensure_one()
        # Doble candado: visibilidad del boton (invisible sin el grupo, en la
        # vista) + verificacion explicita en Python (punto 14). No se usa
        # sudo() en ningun punto de este metodo.
        if not self.env.user.has_group(EXPORT_GROUP):
            raise AccessError(_('No tiene permiso para descargar la trazabilidad de proveedor.'))

        result = self._run_engine()
        xlsx_bytes = self.env['sale.supplier.trace.xlsx.builder'].build(self, result)

        filename = 'trazabilidad_proveedor_ventas_%s.xlsx' % datetime.now().strftime('%Y%m%d_%H%M%S')
        self.write({
            'xlsx_file': base64.b64encode(xlsx_bytes),
            'xlsx_filename': filename,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}
