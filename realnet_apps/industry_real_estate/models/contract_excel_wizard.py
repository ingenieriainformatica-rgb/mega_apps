# models/contract_excel_wizard.py
from odoo import api, fields, models, _
from io import BytesIO
from datetime import datetime, time
import logging
import base64
import re
from html import unescape

_logger = logging.getLogger(__name__)


class ContractExcelWizard(models.TransientModel):
    _name = 'contract.excel.wizard'
    _description = 'Contratos en Excel - Wizard'

    # Nada de filtros: solo preview y export
    line_ids = fields.One2many('contract.excel.wizard.line', 'wizard_id', string='Contratos')
    file_data = fields.Binary(readonly=True)
    filename = fields.Char(readonly=True)

    # ------------------------------
    # Helpers
    # ------------------------------
    # ------------------------------
    # Helpers de formateo/obtención
    # ------------------------------
    def _strip_html(self, html_text):
        """Devuelve texto plano desde HTML (quita tags y &nbsp;)."""
        if not html_text:
            return ''
        # quita tags
        txt = re.sub(r'<[^>]+>', '', str(html_text))
        # decodifica entidades (&nbsp;, etc) y limpia espacios duros
        txt = unescape(txt).replace('\xa0', ' ').strip()
        return txt

    def _concat_names(self, partners):
        """Concatena display_name de un recordset de res.partner."""
        return ', '.join(p.display_name for p in partners if p and p.display_name) or ''

    def _concat_vats(self, partners):
        """Concatena NIT/CC (vat) de un recordset de res.partner."""
        vals = [p.vat for p in partners if getattr(p, 'vat', False)]
        return ', '.join(vals) or ''

    def _owners_list_from_property(self, analytic):
        """Devuelve nombres de propietarios concatenados desde la propiedad."""
        if not analytic:
            return ''
        try:
            lines = getattr(analytic, 'owner_line_ids', self.env['account.analytic.account.owner.line'])
            names = [l.owner_id.display_name for l in lines if l.exists().owner_id]
            return ', '.join(names) or ''
        except Exception:
            return ''
    def _addr_from_property(self, acc):
        """Dirección del inmueble desde la analítica (defensivo)."""
        if not acc:
            return ''
        # Prioriza tu geolocalización personalizada y luego otros posibles campos
        return (
            (getattr(acc, 'x_property_geolocation', '') or '').strip()
            or (getattr(acc, 'street', '') or '').strip()
            or (getattr(acc, 'x_street', '') or '').strip()
        )

    def _city_from_property(self, acc):
        """Municipio del inmueble desde la analítica (defensivo)."""
        if not acc:
            return ''
        # intente por x_city_id (Many2one propio), luego por 'city' si existe en tu modelo
        x_city = getattr(acc, 'x_city_id', False)
        name = ''
        if x_city:
            name = getattr(x_city, 'name', '') or ''
        if not name:
            name = getattr(acc, 'city', '') or getattr(acc, 'x_city', '') or ''
        return name.strip()

    def _canon_from_vars(self, so):
        # Busca variables del contrato (clause.var) si existen
        ClauseVar = self.env['clause.var'].sudo()
        canon = ClauseVar.search([('contract_id', '=', so.id), ('key', '=', 'CONTRATO_CANON')], limit=1)
        canon_txt = ClauseVar.search([('contract_id', '=', so.id), ('key', '=', 'CONTRATO_CANON_LETRAS')], limit=1)
        return (canon and canon.value or ''), (canon_txt and canon_txt.value or '')

    def _commission_value(self, so):
        """Intenta 1) variable COMISION_MENSUAL, 2) parámetro ecoerp, 3) campo suelto."""
        ClauseVar = self.env['clause.var'].sudo()
        v = ClauseVar.search([('contract_id', '=', so.id), ('key', '=', 'COMISION_MENSUAL')], limit=1)
        if v and v.value:
            return v.value
        # fallback: ajustes de EcoERP si los tienes
        if hasattr(so, '_get_ecoerp_settings'):
            try:
                admin_pct, _, _ = so._get_ecoerp_settings()
                if admin_pct is not None:
                    return f"{float(admin_pct):.2f}%"
            except Exception:
                pass
        # último intento: algún campo del SO
        return (getattr(so, 'x_comision_mensual', '') or '')

    def _join_names(self, partners):
        return ', '.join(p.display_name for p in partners) if partners else ''

    def _join_docs(self, partners):
        return ', '.join([p.vat for p in partners if p.vat]) if partners else ''

    def _owners_list(self, acc):
        """Concatena propietarios de la propiedad (owner_line_ids.owner_id)."""
        if not acc or not hasattr(acc, 'owner_line_ids'):
            return ''
        names = [l.owner_id.display_name for l in acc.owner_line_ids if l.owner_id]
        return ', '.join(names)
        
    # 1) Dominio básico (contratos ECOERP + filtros del wizard)
    def _domain_orders(self):
        self.ensure_one()
        dom = [('ecoerp_contract', '=', True)]
        if getattr(self, 'company_id', False):
            dom.append(('company_id', '=', self.company_id.id))
        if getattr(self, 'state', False):
            dom.append(('state', '=', self.state))
        if getattr(self, 'date_from', False):
            dom.append(('date_order', '>=', fields.Datetime.to_string(datetime.combine(self.date_from, time.min))))
        if getattr(self, 'date_to', False):
            dom.append(('date_order', '<=', fields.Datetime.to_string(datetime.combine(self.date_to, time.max))))
        return dom

    # 2) Usa TU helper para armar las líneas
    def _collect_preview_vals(self):
        """Devuelve lista de dicts listos para create() en contract.excel.wizard.line."""
        self.ensure_one()
        dom = self._domain_orders()
        _logger.debug("[ExcelWizard] Dominio usado: %s", dom)
        orders = self.env['sale.order'].sudo().search(dom, order='date_order desc', limit=10000)
        _logger.info("[ExcelWizard] %s contratos encontrados para vista previa", len(orders))

        vals = []
        for so in orders:
            line_vals = self._line_vals_from_so(so)  # <-- TU helper
            line_vals['wizard_id'] = self.id         # injerta el vínculo al wizard
            vals.append(line_vals)
        return vals

    # 3) Refrescar sin cerrar el modal
    def action_refresh(self):
        """Vuelve a calcular la vista previa y reabre el MISMO wizard."""
        self.ensure_one()
        self.sudo().line_ids.exists().unlink()
        lines = self._collect_preview_vals()
        if lines:
            self.env['contract.excel.wizard.line'].sudo().create(lines)

        # Reabrir el mismo popup (evita que “te saque” del wizard)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Importar/Exportar contratos'),
            'res_model': 'contract.excel.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
        
    def _search_contract_orders(self, limit=10000):
        """Dominio único: TODOS los contratos ECOERP (alquiler y administración)."""
        dom = [('ecoerp_contract', '=', True)]
        return self.env['sale.order'].sudo().search(dom, order='date_order desc', limit=limit)

    # Precarga al abrir el wizard (sin guardar aún el registro)
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        orders = self._search_contract_orders()
        lines_cmds = [(0, 0, self._line_vals_from_so(so)) for so in orders]
        res['line_ids'] = lines_cmds
        _logger.info("ContractExcelWizard: precargados %s contratos ECOERP en vista previa.", len(lines_cmds))
        return res

    # Exportar Excel (sin cambios funcionales; solo un log)
    def action_export_xlsx(self):
        self.ensure_one()
        import xlsxwriter
        from datetime import date, datetime
        import base64
        buf = BytesIO()
        wb = xlsxwriter.Workbook(buf, {'in_memory': True})
        ws = wb.add_worksheet('Contratos')

        # Orden 1:1 con tu <list> del XML
        COLS = [
            ('tipo_contrato',     'Tipo de contrato'),
            ('name',              'Número de contrato'),
            ('company_name',      'Empresa'),
            ('state',             'Estado'),
            ('user_name',         'Responsable (vendedor)'),
            ('arrendatario',      'Arrendatario (nombre)'),
            ('arr_doc',           'Documento arrendatario'),
            ('deudores',          'Deudores solidarios (nombres)'),
            ('deudores_docs',     'Documentos de deudores solidarios'),
            ('propietarios',      'Propietarios (lista completa)'),
            ('propiedad',         'Propiedad / Código'),
            ('direccion',         'Dirección del inmueble'),
            ('municipio',         'Municipio del inmueble'),
            ('canon_num',         'Canon (número)'),
            ('canon_let',         'Canon en letras'),
            ('comision',          'Comisión'),
            ('terminos_pago',     'Términos de pago'),
            ('fecha_ini',         'Fecha inicio'),
            ('vig_meses',         'Vigencia (meses)'),
            ('fecha_fin',         'Fecha fin'),
            ('fecha_creacion',    'Fecha creación'),
            ('fecha_actualizacion','Última actualización'),
            ('titulo',            'Título del contrato'),
            ('plantilla',         'Plantilla'),
            ('ref_cliente',       'Referencia del cliente'),
        ]

        # Encabezados
        for c, (_, header) in enumerate(COLS):
            ws.write(0, c, header)

        # Helper: formateo seguro para fechas/datetimes
        def _fmt(v):
            if isinstance(v, (date, datetime)):
                return fields.Datetime.to_string(v) if isinstance(v, datetime) else fields.Date.to_string(v)
            return v if v is not None else ''

        # Filas
        for r, ln in enumerate(self.line_ids, start=1):
            for c, (fname, _) in enumerate(COLS):
                ws.write(r, c, _fmt(getattr(ln, fname, '')))

        wb.close()
        buf.seek(0)
        data = buf.read()
        buf.close()

        # Binary debe ir en base64
        self.write({
            'file_data': base64.b64encode(data),
            'filename': 'contratos.xlsx',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': (
                f"/web/content/?model=contract.excel.wizard&id={self.id}"
                f"&field=file_data&filename_field=filename&download=true"
            ),
            'target': 'self',
        }
    # ------------------------------
    # Mapeo SO -> línea de preview
    # ------------------------------
    def _line_vals_from_so(self, so):
        """Mapea un sale.order -> vals de una línea del wizard (sin wizard_id)."""
        # Deudores (M2M)
        guarantors = getattr(so, 'x_guarant_partner_id', self.env['res.partner'])

        # Propiedad y propietarios
        acc = getattr(so, 'x_account_analytic_account_id', False)
        propietarios = self._owners_list_from_property(acc)

        # Título sin HTML
        titulo_plano = self._strip_html(getattr(so, 'contract_title', ''))

        # ==== NUEVO: usa helpers con fallback ====
        # Dirección / Municipio: primero SO, si no hay usa la propiedad
        addr = getattr(so, 'x_inmueble_direccion', '') or self._addr_from_property(acc)
        muni = getattr(so, 'x_inmueble_municipio', '') or self._city_from_property(acc)

        # Canon: intenta variables; si no, campos x_
        canon_num, canon_let = self._canon_from_vars(so)
        if not canon_num:
            canon_num = getattr(so, 'x_canon_num', '') or ''
        if not canon_let:
            canon_let = getattr(so, 'x_canon_let', '') or ''

        # Comisión: variable -> ajustes ecoerp -> campo x_
        comision_val = self._commission_value(so)
        # =========================================

        return {
            'tipo_contrato': (so.ecoerp_scope or False),  # 'rental' / 'owner'
            'name': so.name,
            'company_name': so.company_id.display_name,
            'state': so.state,
            'user_name': so.user_id.display_name,
            'arrendatario': so.partner_id.display_name,
            'arr_doc': so.partner_id.vat or '',

            'deudores': self._concat_names(guarantors),
            'deudores_docs': self._concat_vats(guarantors),
            'propietarios': propietarios,

            'propiedad': (acc and acc.display_name) or '',
            'direccion': addr,
            'municipio': muni,

            'canon_num': canon_num,
            'canon_let': canon_let,
            'comision': comision_val,
            'terminos_pago': so.payment_term_id.display_name if so.payment_term_id else '',

            'fecha_ini': getattr(so, 'x_rental_start_date', False),
            'vig_meses': getattr(so, 'vigencia_meses', ''),
            'fecha_fin': getattr(so, 'validity_date', False),
            'fecha_creacion': so.create_date,
            'fecha_actualizacion': so.write_date,

            'titulo': titulo_plano,
            'plantilla': so.x_contract_template_id.display_name if so.x_contract_template_id else '',
            'ref_cliente': so.client_order_ref or '',
        }

        
    

    # (Opcional pero recomendado) carga inicial al abrir
    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for wiz in recs:
            wiz.sudo().line_ids.exists().unlink()
            lines = wiz._collect_preview_vals()
            if lines:
                wiz.env['contract.excel.wizard.line'].sudo().create(lines)
        return recs

class ContractExcelWizardLine(models.TransientModel):
    _name = 'contract.excel.wizard.line'
    _description = 'Contratos en Excel - Línea (preview)'

    wizard_id = fields.Many2one('contract.excel.wizard', ondelete='cascade')

    # usa mismos keys que sale.order.ecoerp_scope
    tipo_contrato = fields.Selection([
        ('rental', 'Alquiler'),
        ('owner', 'Administrativo'),
    ], string='Tipo de contrato')

    inmueble = fields.Char(string='Inmueble')

    name = fields.Char()
    company_name = fields.Char()
    state = fields.Char()
    user_name = fields.Char()

    arrendatario = fields.Char()
    arr_doc = fields.Char()
    deudores = fields.Char()
    deudores_docs = fields.Char()
    propietarios = fields.Char()

    propiedad = fields.Char()
    direccion = fields.Char()
    municipio = fields.Char()

    canon_num = fields.Char()
    canon_let = fields.Char()
    comision = fields.Char()
    terminos_pago = fields.Char()

    fecha_ini = fields.Date()
    vig_meses = fields.Char()
    fecha_fin = fields.Date()
    fecha_creacion = fields.Datetime()
    fecha_actualizacion = fields.Datetime()

    titulo = fields.Char()
    plantilla = fields.Char()
    ref_cliente = fields.Char()
