from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from lxml import html, etree
from odoo.addons.industry_real_estate import const
from odoo.tools.float_utils import float_compare, float_round
from functools import lru_cache
import re
import logging
import base64
import io
from markupsafe import Markup
import datetime as dt
import calendar
from odoo.tools.float_utils import float_is_zero


_logger = logging.getLogger(__name__)

def insert_html_before_text_in_div(html_text, html_to_insert):
    try:
        root = html.fragment_fromstring(html_text, create_parent=True)
        first_div = root.find('.//div')

        if first_div is not None:
            # Obtener y eliminar el texto existente
            existing_text = first_div.text or ''
            first_div.text = ''

            # Crear nodo para el HTML a insertar
            insertion_node = html.fragment_fromstring(html_to_insert, create_parent=False)

            # Insertar el nodo deseado primero
            first_div.insert(0, insertion_node)

            # Luego, añadir el texto original después
            if existing_text.strip():
                tail_node = etree.Element("span")
                tail_node.text = existing_text
                first_div.insert(1, tail_node)

        return html.tostring(root, encoding='unicode', method='html')

    except Exception as e:
        return html_text

CTX_KEY = 'skip_fill_vars'
_PREVIEW_CTX_FLAG = 'skip_preview_attachment'
_PREVIEW_ONCE_KEY = 'preview_pdf_already_done'
FIELDS_PREVIEW_AFFECT = {
    'sale_clause_line_ids', 'clause_var_ids',      # contenido del contrato
    'partner_id', 'x_account_analytic_account_id',
    'x_guarant_partner_id', 'x_rental_start_date',
    'validity_date', 'vigencia_meses', 'company_id', 'currency_id',
    }


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_related_buildings_ids = fields.Many2many(
        comodel_name='x_buildings',
        string='Related Buildings'
    )

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Arrendatario",
        tracking=True,
        # default=lambda self: self.env.company.partner_id.id,  # ← siempre la compañía
    )

     # Arrendador: siempre compañía
    partner_lessor_id = fields.Many2one(
        'res.partner',
        string='Arrendador',
        default=lambda self: self.env.company.partner_id,   # compañía activa → su partner
        domain="[('is_company','=', True)]",
    )

    # Representante: contacto (persona) hijo de la compañía
    partner_lessor_contact_id = fields.Many2one(
        'res.partner',
        string='Contacto arrendador',
        default=lambda self: self.env.user.partner_id,      # partner del usuario actual
    )

    ecoerp_contract = fields.Boolean(
        string='Contrato ECOERP',
        default=False,
        index=True,
        help='Si está activo, este pedido es un contrato de ECO ERP y no debe verse en Ventas.'
    )
    
    x_guarant_partner_id = fields.Many2many(
        'res.partner',
        string="Deudores solidarios",
        relation='sale_order_guarant_partner_rel',  # nombre de tabla único
        column1='sale_order_id',                   # columna para sale.order
        column2='partner_id',                      # columna para res.partner
    )

    x_contract_template_id = fields.Many2one(
        'contract.template', string='Documento pdf del contrato'
    )

    contract_title = fields.Html(string='Titulo del contrato')
    # contract_preface = fields.Html(string='Prefacio del contrato')
    contract_id = fields.Many2one('x.contract', string='Contrato', index=True)
    contract_sign_state = fields.Selection(related='contract_id.sign_request_id.state', readonly=True)
    contract_is_signed = fields.Boolean(compute='_compute_contract_is_signed', store=False)
    # Contador para el smart button
    sign_request_count = fields.Integer(
        string='Firmas',
        compute='_compute_contract_sign_request_ids',
        store=False,
    )
    signed_docs_count = fields.Integer(
        string="Docs firmados",
        compute="_compute_signed_docs_count",
        compute_sudo=True,
    )
    # Lista de solicitudes de firma, tomada del contrato
    contract_sign_request_ids = fields.One2many(
        'sign.request', 'x_contract_id',
        string='Firmas del contrato',
        compute='_compute_contract_sign_request_ids',
        readonly=True, store=False, copy=False,
    )

    x_delivery_card_line_ids = fields.One2many(
        'x.delivery.reception.line',
        'sale_order_id',
        string="Entrega",
    )

    x_reception_card_line_ids = fields.One2many(
        'x.delivery.reception.line',
        'sale_order_id',
        string="Recepción",
    )

    sale_clause_line_ids = fields.One2many(
        'clause.line',
        'sale_order_id',
        string='Cláusulas del Contrato',
        domain="[('is_master', '=', False)]"
    )

    clause_var_ids = fields.One2many(
        'clause.var',
        'contract_id',
        string='Variables de Contrato'
    )

    rendered_clauses = fields.Html(
        string="Texto de cláusulas renderizadas",
        sanitize=False,
        compute='_compute_rendered_clauses',
        store=True,
        readonly=True,
    )

    x_custom_state = fields.Selection(
        selection=const.ESTATES,
        string='Estado del contrato',
        compute='_compute_x_custom_state',
        store=True,
        readonly=True,
        tracking=True,
    )

    # Visibilidad de las pestañas según el estado
    can_see_delivery_tab = fields.Boolean(
        compute='_compute_can_see_delivery_tab',
        store=False
    )

    can_see_reception_tab = fields.Boolean(
        compute='_compute_can_see_reception_tab',
        store=False
    )
    
    modification_type = fields.Selection([
        ('none', 'Contrato original'),
        ('otrosi', 'Otrosí (Modificación)'),
        ('transaccion', 'Contrato de Transacción'),
    ], string="Tipo de Modificación", default='none',
       help="Determina si este contrato es un contrato base, un otrosí o un contrato de transacción.")

    contract_annex_ids = fields.One2many(
        'contract.annex', 'sale_order_id', string="Anexos del contrato"
    )
    
    """ validación de agregar item en entrega - recepción si no existen contratos """
    # variable condicional
    can_add_inventory = fields.Boolean(
        string="Puede agregar a inventario",
        compute="_compute_can_add_inventory",
        store=True # en false para que no se mantenga constante y pueda aplicar el compute
    )
    # anexo del historial de inventario para entrega y recepcion
    history_ids = fields.One2many(
        comodel_name='property.item.history',
        inverse_name='property_id',
        string='Historial de inventario'
    )
    
    """ propietarios y beneficiarios por propiedad"""
    
    # Lista de partners propietarios candidatos para esta orden (según la propiedad elegida)
    owner_candidate_ids = fields.Many2many(
        'res.partner', string='Propietarios candidatos', compute='_compute_owner_candidates', store=False
    )

    ecoerp_scope = fields.Selection(
        [('rental', 'Alquiler'), ('owner', 'Propietario')],
        string="Ámbito ECOERP",
        default='rental',
        index=True
    )
    x_account_analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Propiedad",
        required=False,
        domain="[('x_is_property', '=', True), ('x_is_available','=',True)]",
        context={'default_x_is_property': True},
    )# variable propiedad de contratos definido al inicio del desarrollo
    property_id = fields.Many2one(related="x_account_analytic_account_id", string='Propiedad', store=True)
    property_item_id = fields.Many2one('property.item', string="Ítem de propiedad")    
    owner_responsibility_ids = fields.One2many(
        'sale.order.owner.responsibility', 'order_id', string="Responsabilidades económicas"
    )
    x_rental_start_date = fields.Date(string="Fecha inicio")
    date_owner_start = fields.Date(string="Fecha inicio (propietario)")# por definir
    date_owner_end = fields.Date(string="Fecha final (propietario)")# por definir
    sign_template_id = fields.Many2one('sign.template', string="Plantilla de contrato (propietario)")    
    amount_owner_base = fields.Monetary(string="Base liquidable", currency_field='currency_id', compute='_compute_owner_base')
    
    cobro_papeleria = fields.Boolean(string="Cobro papelería", default=True)
    cobro_adicional = fields.Boolean(string="Cobros adicionales", default=False)
    cobro_comision_inicial = fields.Boolean(string="Cobro comisión inicial", default=True)
    #comision contrato
    comision_inmobiliaria = fields.Boolean(string="Comisión inmobiliaria", default=False)
    company_commission = fields.Float(
        string="Comisión compañía (%)",
        related="company_id.porcentaje_comision_inmobiliaria",
        readonly=True,
        digits=(16, 2),
    )
    comision_inmobiliaria_porcentaje = fields.Float(
        string="Comisión inmobiliaria (%)",
        compute="_compute_comision_inmobiliaria_porcentaje",
        store=True,
        readonly=False,
        digits=(16, 2),
        help="Si 'Usar comisión de la compañía' está activo, este valor se copia "
             "desde la compañía. Si no, puedes sobrescribirlo."
    )
    #calculo ipc contrato
    cobro_adicional_ipc = fields.Boolean(string="IPC", default=False)
    cobro_adicional_ipc_re = fields.Boolean(string="IPC", default=False)
    monto_adi_ipc = fields.Float(string="Monto adicional", digits=(16, 2))
    monto_ipc = fields.Float(string="", digits=(16, 2))
    monto = fields.Float(string="Monto", digits=(16, 2))
    #administracion PH
    cobro_comision_admin_ph = fields.Boolean(string="Comisión adm. PH", default=True)
    administracion_ph = fields.Float(string="Administracion PH", digits=(16, 2))
    monto_comision_admin_ph = fields.Float(string="", digits=(16, 2))
    #servicios publicos 
    servicios_publicos = fields.Boolean(string="Servicios", default=False)
    #Internet 
    internet = fields.Boolean(string="Internet", default=False)
    monto_internet = fields.Float(string="Monto Internet", digits=(16, 2))
    #Tv 
    tv = fields.Boolean(string="Tv", default=False)
    monto_tv = fields.Float(string="Monto Tv", digits=(16, 2))
    #Administracion-sostenimiento 
    administracion_sostenimiento = fields.Boolean(string="Administracion-sostenimiento", default=False)
    monto_administracion_sostenimiento = fields.Float(string="Monto Administracion-sostenimiento", digits=(16, 2))
    #costo transaccion
    costo_transaccion = fields.Boolean(string="Costo transaccion", default=False)
    costo_transaccion_monto = fields.Float(string="", digits=(16, 2))
    #4x1000 
    cuatropormil = fields.Boolean(string="4x1000", default=False)

    
    
    
    porcentaje_ipc = fields.Float(
        string="Porcentaje IPC (%)",
        related='company_id.porcentaje_ipc',
        readonly=False
    )
    porcentaje_adicional_ipc = fields.Float(
        string="Porcentaje adicional al IPC (%)",
        related='company_id.porcentaje_adicional_ipc',
        readonly=False
    )
    porcentaje_cobros_adicionales = fields.Float(
        string="Porcentaje de cobros adicionales (%)",
        related='company_id.porcentaje_cobros_adicionales',
        readonly=False
    )
    monto_adicional_paleria = fields.Integer(
        string="Monto adicional palería",
        related='company_id.monto_adicional_paleria',
        readonly=False
    )
    monto_cobros_adicionales = fields.Integer(
        string="Cobros adicionales (monto fijo)",
        related='company_id.monto_cobros_adicionales',
        readonly=False
    )
    porcentaje_comision_inicial = fields.Float(
        string="Porcentaje comisión inicial (%)",
        related='company_id.porcentaje_comision_inicial',
        readonly=False
    )
    admin_pct = fields.Float(
        string="Comisión inmobiliaria (%)",
        related='company_id.porcentaje_comision_inmobiliaria',
        store=False, readonly=False  # o store=True si quieres buscar/filtrar
    )
    ecoerp_product_canon_id = fields.Many2one(
        'product.product',
        related='company_id.ecoerp_product_canon_id',
        store=False, readonly=False
    )
    ecoerp_product_owner_payment_id = fields.Many2one(
        'product.product',
        related='company_id.ecoerp_product_owner_payment_id',
        store=False, readonly=False
    )
    
    invoice_count = fields.Integer(
        string="Number of Invoices",
        compute="_compute_invoice_count",
        store=True,
    )
    

    # # ====== BLOQUE: Calculo canon*1*ipc+monto ====== 
    # # ==========================================
    # Resultado (solo lectura en vista)
    resultado_monto_ipc = fields.Float(
        string="Resultado final",
        digits=(16, 2),
        compute="_compute_resultado_monto_ipc",
        
    )
    
    gantt_color = fields.Selection([
        ('gray', 'Finalizado'),
        ('green', 'En progreso'),
        ('yellow', 'Borrador'),
    ], compute='_compute_gantt_color', store=False)
    
    @api.depends('company_id', 'comision_inmobiliaria')
    def _compute_comision_inmobiliaria_porcentaje(self):
        """Sincroniza desde la compañía SOLO cuando la bandera está activa.
        Deja intacto cualquier valor manual cuando la bandera está desactivada.
        """
        for rec in self:
            if rec.comision_inmobiliaria and rec.company_id:
                rec.comision_inmobiliaria_porcentaje = \
                    rec.company_id.porcentaje_comision_inmobiliaria

    @api.onchange('company_id')
    def _onchange_company_id_set_commission(self):
        """En formularios, al cambiar de compañía, vuelve a proponer el valor si procede."""
        for rec in self:
            if rec.comision_inmobiliaria and rec.company_id:
                rec.comision_inmobiliaria_porcentaje = \
                    rec.company_id.porcentaje_comision_inmobiliaria

    def _compute_gantt_color(self):
        for rec in self:
            _logger.info(" REC %s ",rec.state,rec.gantt_color)
            if rec.state == 'done':
                rec.gantt_color = 'gray'
            elif rec.state == 'sale':
                rec.gantt_color = 'green'
            else:
                rec.gantt_color = 'yellow'                
            # _logger.info(" REC %s -  %s",rec.state,rec.gantt_color)
    
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for order in self:
            order.invoice_count = len(order.invoice_ids)

    @api.depends('canon_property', 'monto_adi_ipc', 'monto_ipc', 'x_uso_destino_rel')
    def _compute_resultado_monto_ipc(self):
        """
        Fórmula: resultado = canon_property * 1 * monto_adi_ipc + monto_ipc
        (equivale a: canon_property * monto_adi_ipc + monto_ipc)

        Solo aplica para uso comercial; en otros usos deja 0.0
        """
        today = fields.Date.context_today(self)
        year = fields.Date.to_date(today).year  # asegura entero a partir del date
        ipc_rec = self.env['ipc.history'].search([('year', '=', year - 1)], order='id desc', limit=1)
        ipc_default = float(ipc_rec.ipc_value) if ipc_rec and ipc_rec.ipc_value else 0.0
        for rec in self:
            if not rec.exists():
                continue
            if rec.x_uso_destino_rel == 'commercial':
                base = rec.canon_property or 0.0
                factor = ipc_default+rec.monto_ipc or 0.0
                rec.resultado_monto_ipc = base * factor 
            else:
                rec.resultado_monto_ipc = 0.0
                
    
    # # ====== BLOQUE: Calculo canon*1*ipc+monto  ===========
    # # ==========================================

    # # ====== BLOQUE:arrendador por defecto ===========
    # # ==========================================
    
    # ====== BLOQUE: pdf en chatter ===========
    # ==========================================
    
    # ===== Panel de variables (lo tuyo) =====
    contract_var_lines = fields.One2many(
        'contract.var', 'contract_id',
        string="Variables del contrato (panel)",
        copy=False,
    )
    
    x_uso_destino_rel = fields.Selection(
        related='x_account_analytic_account_id.uso_destino',
        string='Uso del inmueble (propiedad)',
        readonly=False,
        store=False,          # déjalo sin store para que refresque en vivo al cambiar la propiedad
    )
    
    end_date = fields.Date(
        string="Vencimiento (alias)",
        related='validity_date',
        store=True,        # guarda el valor para búsquedas/agrupaciones
        readonly=False,    # si lo pones False, podrás editar y Odoo escribirá en validity_date
    )
    canon_property = fields.Integer(
        string="Canon de la propiedad",
        related='x_account_analytic_account_id.canon',
        store=False, readonly=False  # o store=True si quieres buscar/filtrar
    )
    date_increment = fields.Date(
        string="Fecha incremento",
        compute="_compute_date_increment",
        store=True,
    )
    
    increase_percent = fields.Float(
        related="porcentaje_ipc",
        store=False
    )
    
    @api.model
    def _apply_rent_increase(self):
        """
        Incrementa líneas de canon cuando toca, usando el IPC del año anterior o
        el monto específico configurado por contrato (monto_ipc si cobro_adicional_ipc=True).

        Soporta:
        - Llamado por cron / Server Action: env['sale.order']._apply_rent_increase()
        - Llamado manual sobre pedidos seleccionados: self (recordset)
        """
        today = fields.Date.context_today(self)
        year = fields.Date.to_date(today).year  # asegura entero a partir del date

        # 1) Traer IPC del año anterior (un solo registro)
        ipc_rec = self.env['ipc.history'].search([('year', '=', year - 1)], order='id desc', limit=1)
        _logger.info("IPC record encontrado: %s", ipc_rec and ipc_rec.display_name or "N/A")
        ipc_default = float(ipc_rec.ipc_value) if ipc_rec and ipc_rec.ipc_value else 0.0

        # 2) Determinar las órdenes a procesar
        if self and self.ids:
            orders = self
        else:
            orders = self.env['sale.order'].search([
                ('date_increment', '<=', today),
                ('state', 'in', ('sale', 'done')),
            ])

        if not orders:
            _logger.info("No hay pedidos a los que aplicar incremento a fecha %s.", today)
            return

        # Log seguro (evita Expected singleton)
        try:
            _logger.info("Aplicando incremento a %s pedidos: %s",
                         len(orders), ", ".join(orders.mapped('name')))
        except Exception:
            pass

        # 3) Resolver producto de canon vía XMLID (defensivo frente a template/variant)
        rent_prod = self.env.ref('industry_real_estate.product_product_42', raise_if_not_found=False)
        if rent_prod and rent_prod._name == 'product.template':
            rent_prod = rent_prod.product_variant_id
        if not rent_prod or rent_prod._name != 'product.product':
            raise UserError(_("No se encontró el producto 'Tarifa de alquiler' (XMLID industry_real_estate.product_product_42)."))

        # 4) Procesar por lotes para mayor resiliencia en cron
        BATCH = 100
        rate = ipc_default
        for i in range(0, len(orders), BATCH):
            batch = orders[i:i+BATCH]
            with self.env.cr.savepoint():
                for order in batch:
                    try:
                        # Toma el IPC de la orden si tiene cobro adicional, si no el histórico
                        if getattr(order, 'cobro_adicional_ipc', False):
                            rate = float(ipc_default+order.monto_ipc)
                        if float_is_zero(rate, precision_digits=2):
                            order.message_post(body=_("Incremento omitido: tasa 0%% para %s.") % (order.name,))
                            # (opcional) mover fecha para evitar reevaluar a diario
                            order.write({'date_increment': (order.date_increment or today) + relativedelta(months=12)})
                            continue

                        # Filtrar líneas de canon por producto exacto
                        rent_lines = order.order_line.filtered(lambda l: l.product_id == rent_prod)
                        if not rent_lines:
                            order.message_post(body=_("No se encontraron líneas de canon para aplicar incremento (%s%%).") % rate)
                            order.write({'date_increment': (order.date_increment or today) + relativedelta(months=12)})
                            continue

                        # Aplicar incremento
                        for line in rent_lines:
                            new_price = line.price_unit * (1.0 + (rate / 100.0))
                            line.price_unit = new_price
                            # Si mantienes un campo espejo en la orden:
                            if 'canon_property' in order._fields:
                                order.canon_property = new_price

                        # Próxima fecha de incremento
                        next_date = (order.date_increment or today) + relativedelta(months=12)
                        order.write({'date_increment': next_date})

                        order.message_post(
                            body=_("Incremento aplicado automáticamente: %(rate).2f%%. Próxima fecha: %(next)s") % {
                                'rate': rate,
                                'next': fields.Date.to_string(next_date),
                            }
                        )
                    except Exception as e:
                        _logger.exception("Fallo aplicando incremento en %s (id=%s): %s", order.name, order.id, e)
                        order.message_post(body=_("Error aplicando incremento: %s") % (str(e),))
                        continue
    
    @api.depends('x_rental_start_date')
    def _compute_date_increment(self):
        for rec in self:
            if not rec.exists():
                continue
            rec.date_increment = (
                rec.x_rental_start_date and
                (rec.x_rental_start_date + relativedelta(months=12)) or False
            )
            
    @api.onchange('x_rental_start_date')
    def _onchange_x_rental_start_date_sync(self):
        """En formulario: al cambiar la fecha de inicio, fijamos date_order al mismo día."""
        if self.x_rental_start_date:
            self.date_order = fields.Datetime.to_datetime(self.x_rental_start_date)
    def _sync_dates_from_start(self):
        """Reuso en create/write para asegurar consistencia en cualquier vía."""
        for rec in self:
            if rec.x_rental_start_date:
                rec.date_order = fields.Datetime.to_datetime(rec.x_rental_start_date)
                rec.date_increment = rec.x_rental_start_date + relativedelta(months=12)
            else:
                rec.date_increment = False
    
    @api.onchange('company_id')
    def _onchange_company_set_lessor(self):
        if self.company_id:
            self.partner_lessor_id = self.company_id.partner_id
            
            
    
    
    # =======================
    #  PDF / CHATTER HANDLERS (BLOQUE CORREGIDO)
    # =======================

    def _attach_or_replace_preview_pdf(self, pdf_bytes):
        """
        MODIFICADO: Ahora crea SIEMPRE un nuevo adjunto con timestamp para mantener el historial.
        Ya no busca ni reemplaza, garantizando que el chatter sea un histórico fiel.
        """
        self.ensure_one()
        if not pdf_bytes:
            return self.env['ir.attachment']

        # Generar nombre único con timestamp para preservar el historial
        timestamp = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        name = f"contrato_{self.name}_({timestamp}).pdf"

        Attachment = self.env['ir.attachment'].sudo()
        vals = {
            'name': name,
            'res_model': 'sale.order',
            'res_id': self.id,
            'type': 'binary',
            'mimetype': 'application/pdf',
            'datas': base64.b64encode(pdf_bytes),
            'company_id': self.company_id.id,
        }
        
        # Siempre crea un nuevo adjunto, nunca busca ni reemplaza.
        return Attachment.create(vals)

    def _generate_preview_pdf_bytes(self, html_override=None):
        """
        SIN CAMBIOS. Este método ya es correcto. Confía en que los datos
        fueron persistidos y refrescados por el orquestador que lo llama.
        """
        self.ensure_one()
        ctx = dict(self.env.context or {})

        # 1) Preferir override explícito
        html = (html_override or '').strip()

        # 2) Si no hay override, intentar rendered_clauses
        #    Se asume que este valor es fresco gracias al invalidate_recordset previo.
        if not html:
            html = (getattr(self, 'rendered_clauses', '') or '').strip()

        # 3) Fallback crítico en create(): construir HTML “en caliente”
        if not html and hasattr(self, '_build_preview_html_now'):
            try:
                preview_map = self._build_preview_html_now() or {}
                html = (preview_map.get(self.id) or '').strip()
            except Exception:
                _logger.exception("Fallo al construir preview HTML con _build_preview_html_now()")

        if not html:
            _logger.debug("No hay HTML de previsualización disponible para %s", self.display_name)
            return b''

        ctx['preview_html'] = html

        report = self.env.ref('industry_real_estate.action_report_contract_preview', raise_if_not_found=False)
        if not report:
            _logger.error("Report action_report_contract_preview no encontrado.")
            return b''

        # La llamada a _render_qweb_pdf que tienes es correcta
        rendered, _ = report.with_context(ctx)._render_qweb_pdf(report.report_name, res_ids=[self.id])
        return rendered or b''
    
    @api.onchange('partner_lessor_id')
    def _onchange_partner_lessor_id(self):
        """Preselecciona un contacto de la empresa (si existe)."""
        for rec in self:
            rec.partner_lessor_contact_id = False
            if rec.partner_lessor_id:
                # Toma el primer contacto 'persona' útil (type contact/other)
                contact = rec.partner_lessor_id.child_ids.filtered(
                    lambda p: not p.is_company and p.type in ('contact', 'other') and p.active
                )[:1]
                rec.partner_lessor_contact_id = contact.id if contact else False

    @api.constrains('partner_lessor_id', 'partner_lessor_contact_id','ecoerp_contract')
    def _check_lessor_contact_company(self):
        """El representante debe pertenecer a la misma compañía."""
        if self.env.context.get('active_model')=='contract.excel.wizard':
            return

        for rec in self:
            if rec.ecoerp_contract:
                if rec.partner_lessor_id and rec.partner_lessor_contact_id:
                    if rec.partner_lessor_contact_id.commercial_partner_id != rec.partner_lessor_id.commercial_partner_id:
                        raise ValidationError(_("El representante debe pertenecer a la misma compañía del arrendador."))
    

    def action_update_contract_preview_pdf(self, html_override=None):
        """
        CORREGIDO: Orquestador principal.
        - Fuerza el guardado (flush) y recálculo (invalidate) ANTES de renderizar.
        - Llama al método de adjunto que preserva el historial.
        - Gestiona las guardias de contexto correctamente para evitar loops.
        """
        debug = bool(self.env.context.get('preview_debug'))

        for order in self:
            # Guardia de contexto: saltar si estamos en un stack interno y no nos han dado permiso explícito.
            if order.env.context.get(_PREVIEW_CTX_FLAG) and not order.env.context.get(_PREVIEW_ONCE_KEY):
                continue

            try:
                # --- PASO 1 (CLAVE): Forzar guardado de datos y recálculo del compute ---
                order._fill_fixed_clause_vars()
                # Usar order.env.cr.flush() es una API válida y robusta en Odoo 18
                order.env.cr.flush()
                
                order.invalidate_recordset(['rendered_clauses'])
                order._compute_rendered_clauses() #renderiza clausulas justo antes de generar
                
                # --- S1: Generar PDF con los datos ya actualizados ---
                pdf = order._generate_preview_pdf_bytes(html_override=html_override)
                if debug:
                    order.message_post(body=f"[S1] pdf_len={len(pdf) if pdf else 0}", subtype_xmlid='mail.mt_note')
                if not pdf:
                    continue

                # --- S2: Crear un NUEVO adjunto (lógica ahora dentro del método modificado) ---
                att = order._attach_or_replace_preview_pdf(pdf)
                if debug:
                    order.message_post(body=f"[S2] att_id={att.id}", subtype_xmlid='mail.mt_note')

                # --- S3: Postear en chatter ---
                order.message_post(
                    body=_("Se ha generado una nueva previsualización del contrato."),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                    attachment_ids=[att.id],
                )
                if debug:
                    order.message_post(body=f"[S3] posted att_id={att.id}", subtype_xmlid='mail.mt_note')

            except Exception as e:
                _logger.exception("Error en el flujo de generación de PDF para %s: %s", order.display_name, e)
                if debug:
                    order.message_post(body=f"[ERROR-PDF] {e}", subtype_xmlid='mail.mt_note')
                continue
    # ====== BLOQUE: pdf en chatter ============
    # ==========================================
    
    
    
    
    # =========================================================
    # BLOQUE: Cláusulas automáticas (Odoo 18)
    # =========================================================

    # Usamos esta clave para evitar recursiones al escribir desde helpers
    CTX_KEY = 'skip_clause_autofill'

    trade_name = fields.Char(string="Nombre comercial")

    # ---------------------------------------------------------
    # Helpers básicos (no tocan la DB si no es necesario)
    # ---------------------------------------------------------
    @staticmethod
    def _strip_val(val):
        """Normaliza strings con espacios duros y trim."""
        return (str(val or '').replace('\xa0', '')).strip()
    
    @staticmethod
    @lru_cache(maxsize=64)
    def _num_to_words_es(n: int) -> str:
        try:
            from num2words import num2words
            return num2words(n, lang='es')
        except Exception:
            return str(n)

    def _canon_to_words(self, amount):
        """
        Convierte un número a 'xxx pesos con YY/100'.
        No lanza, y no escribe en DB.
        """
        if amount in (False, None, ''):
            return ''
        s = self._strip_val(amount)
        # Parse tolerante: "1.234,56" | "1234,56" | "1,234.56" | "1234.56"
        try:
            amt = float(s.replace('.', '').replace(',', '.'))
        except Exception:
            try:
                amt = float(s.replace(',', ''))
            except Exception:
                return ''

        entero = int(abs(amt))
        cents  = int(round((abs(amt) - entero) * 100))

        entero_txt = self._num_to_words_es(entero)
        #entero_txt = self._num_to_words_es(entero)
        # Si quieres el formato extendido, cambia la línea de retorno
        return f"{entero_txt} pesos"

    def _var_map(self, record):
        """Crea mapa key->record con las cláusulas ya cargadas en memoria."""
        return {v.key: v for v in record.clause_var_ids if v.key}

    def _set_if_empty(self, rec, value):
        """
        Escribe value en la línea de variable solo si está vacía.
        Protegido con CTX_KEY para evitar recursión de onchange/write.
        """
        if rec and not (rec.value or '').strip():
            rec.with_context(**{CTX_KEY: True}).write({'value': value or ''})

    # ---------------------------------------------------------
    # Sincroniza CONTRATO_CANON → CONTRATO_CANON_LETRAS
    # ---------------------------------------------------------
    def _sync_canon_letras(self, canon_override=None):
        """
        Completa CONTRATO_CANON_LETRAS si:
        - Existe la variable de letras
        - Está vacía
        - Hay canon (o canon_override)
        No crea líneas nuevas (lo menos invasivo).
        """
        for o in self:
            existing   = self._var_map(o)
            canon_rec  = existing.get('CONTRATO_CANON')
            letras_rec = existing.get('CONTRATO_CANON_LETRAS')

            canon_val = canon_override
            if canon_val is None and canon_rec:
                canon_val = canon_rec.value

            if not canon_val or not letras_rec:
                continue  # nada que hacer

            # solo si está vacío (no pisamos al usuario)
            if not (letras_rec.value or '').strip():
                letras_val = o._canon_to_words(canon_val)
                if letras_val:
                    letras_rec.with_context(**{CTX_KEY: True}).write({'value': letras_val})

    # ---------------------------------------------------------
    # ONCHANGE (solo UI)
    # ---------------------------------------------------------
    @api.onchange('clause_var_ids')
    def _onchange_canon_autofill(self):
        """
        Cuando el usuario edita líneas en el O2M, intentamos “en memoria”
        completar el valor de letras si está vacío.
        """
        for o in self:
            # leemos el canon de las líneas in-memory (incluye NewId)
            canon_val = None
            for v in o.clause_var_ids:
                if v.key == 'CONTRATO_CANON':
                    canon_val = v.value
                    break
            if canon_val:
                o._sync_canon_letras(canon_val)

    # ---------------------------------------------------------
    # Autocompletado de variables “fijas”
    # ---------------------------------------------------------
    def _fill_fixed_clause_vars(self):
        """
        Autocompleta variables fijas SIN sobreescribir valores del usuario.
        Solo escribe si la variable existe y está vacía.
        """
        if self.env.context.get(CTX_KEY):
            return  # prevenimos reentradas

        for o in self:
            if not o.clause_var_ids:
                continue

            # Helpers locales
            def put(key, compute):
                self._set_if_empty(existing.get(key), (compute() or ''))            
            def _addr():
                try:
                    x = (getattr(acc, 'x_property_geolocation', '') or '').strip()
                except Exception:
                    x = ''
                return x or (getattr(acc, 'street', '') or '').strip()
            def _mun():
                try:
                    x_city = getattr(acc, 'x_city_id', False)
                    name = (getattr(x_city, 'name', '') or '').strip() if x_city else ''
                except Exception:
                    name = ''
                return name or (getattr(acc, 'city', '') or '').strip()            
            def _date_to_words(dt):
                if not dt:
                    return ''
                try:
                    from num2words import num2words
                    day   = int(dt.day)
                    month = dt.strftime('%B').lower()
                    year  = int(dt.year)
                    return f"{num2words(day, lang='es')} de {month} de {num2words(year, lang='es')}"
                except Exception:
                    try:
                        from odoo.tools import format_date
                        return format_date(self.env, dt, lang_code=lang)
                    except Exception:
                        return dt.strftime('%Y-%m-%d')
            existing = self._var_map(o)
            
            partner = o.partner_id
            company = o.company_id
            acc     = o.x_account_analytic_account_id
            owners  = getattr(acc, 'owner_line_ids', False)
            start   = o.x_rental_start_date
            end     = o.validity_date
            lang    = o.env.user.lang or 'es_CO'
            # ========================================
            # --------------- PROPIEDAD ---------------
            # ========================================
            put("INMUEBLE_DIRECCION", _addr)
            put("INMUEBLE_MUNICIPIO", _mun)
            put("MUNICIPIO",          _mun)
            put("SOLICITUD_DESTINO_INMUEBLE",     lambda: acc.uso_destino if acc else '')
            put("CONTRATO_CANON",     lambda: acc.canon if acc else '')
            # ---------- canon → letras (solo si letras existe y está vacía)
            try:
                self._sync_canon_letras()
            except Exception:
                _logger.exception("No se pudo autocompletar CONTRATO_CANON_LETRAS")
            put("INMUEBLE_NUMERO_CUARTO_UTIL",     lambda: acc.cuarto_util if acc else '')
            put("INMUEBLE_NUMERO_PARQUEADERO",     lambda: acc.x_parking_spaces if acc else '')
            put("PROYECTO_NOMBRE",     lambda: acc.x_property_building_id.x_name if acc else '')
            # ========================================
            # --------------- CONTACTOS ---------------
            # ========================================
            # --------------- ARRENDATARIO ---------------
            put("ARRENDATARIO_NOMBRE",     lambda: partner.display_name if partner else '')
            put("ARRENDATARIO_DOCUMENTO",  lambda: partner.vat or '')
            put("ARRENDATARIO_ENCABEZADO", lambda: f"{partner.display_name} - {partner.vat}"
                                                if (partner and partner.vat) else (partner.display_name or ''))
            put("LINEA_TELEFONICA",  lambda: partner.phone or partner.mobile or '')
            
            # --------------- DEUDORES SOLIDARIOS ---------------
            if o.x_guarant_partner_id:
                noms = ', '.join(p.display_name for p in o.x_guarant_partner_id)
                docs = ', '.join(filter(None, [p.vat for p in o.x_guarant_partner_id]))
                put("DEUDORES_SOLIDARIOS",        lambda: noms)
                put("NOMBRE_DEUDOR_SOLIDARIO",    lambda: noms)
                put("DOCUMENTO_DEUDOR_SOLIDARIO", lambda: docs)
            # --------------- PROPIETARIOS ---------------
            if owners:
                nombres = ', '.join(ol.owner_id.display_name for ol in owners if ol.owner_id)
                put("PROPIETARIOS_LISTA_COMPLETA", lambda: nombres)
                put("NOMBRE_ARRENDADOR",           lambda: company.partner_id.display_name if company and company.partner_id else '')
            # ========================================
            # --------------- CONTRATO ---------------
            # ========================================
            # --------------- FECHAS EN LETRAS ---------------   
            put("FECHA_INICIO_CONTRATO_LETRAS", lambda: _date_to_words(start))
            put("FECHA_FIN_CONTRATO_LETRAS",   lambda: _date_to_words(end))
            # --------------- COMISIÓN MENSUAL ---------------
            if hasattr(o, '_get_ecoerp_settings'):
                try:
                    # Soporta retorno (admin_pct, prod1, prod2) o solo admin_pct
                    settings = o._get_ecoerp_settings()
                    admin_pct = settings[0] if isinstance(settings, (list, tuple)) else settings
                except Exception:
                    admin_pct = None
                put("COMISION_MENSUAL", lambda: f"{float(admin_pct):.2f}%" if admin_pct is not None else '')
            # --------------- DURACIÓN ---------------
            if getattr(o, 'vigencia_meses', False):
                self._set_if_empty(existing.get("CONTRATO_DURACION"), str(int(o.vigencia_meses)))

    # ---------------------------------------------------------
    # ONCHANGE que dispara el autocompletado “fijo”
    # ---------------------------------------------------------
    @api.onchange('x_contract_template_id')
    def _onchange_contract_template_fill_vars(self):
        for rec in self:
            if rec.x_contract_template_id and hasattr(rec, '_generate_clause_vars'):
                rec.with_context(**{CTX_KEY: True})._generate_clause_vars()
            rec._fill_fixed_clause_vars()

    @api.onchange('partner_id', 'x_account_analytic_account_id', 'x_guarant_partner_id',
                'x_rental_start_date', 'validity_date', 'vigencia_meses')
    def _onchange_fill_fixed_vars(self):
        self._fill_fixed_clause_vars()

    # ---------------------------------------------------------
    # Escribe valores iniciales del usuario (no invasivo)
    # ---------------------------------------------------------
    def _apply_initial_user_vars(self, initial_vars: dict):
        """
        Escribe (key->value) que el usuario digitó en la UI sobre los clause.var
        ya creados. Crea la variable si no existe.
        """
        ClauseVar = self.env['clause.var'].sudo()
        for order in self:
            if not initial_vars:
                continue
            existing = self._var_map(order)
            for k, v in initial_vars.items():
                if not k:
                    continue
                rec = existing.get(k)
                if rec:
                    rec.with_context(**{CTX_KEY: True}).write({'value': v or ''})
                else:
                    ClauseVar.with_context(**{CTX_KEY: True}).create({
                        'contract_id': order.id,
                        'key': k,
                        'value': v or '',
                    })

    # =========================================================
    # BLOQUE: Cláusulas automáticas (Odoo 18)
    # =========================================================
    

    # ====== BLOQUE: Vigencia de contrato ======
    # ÚNICO campo nuevo editable por el usuario
    vigencia_meses = fields.Integer(
        string='Vigencia (meses)',
        default=12,
        help='Cantidad de meses de vigencia del contrato.'
    )

    # Sobrescribimos el campo nativo para calcularlo en servidor y persistirlo
    validity_date = fields.Date(
        string='Vencimiento',
        compute='_compute_validity_date',
        store=True,
        readonly=True,
    )

    @api.depends('x_rental_start_date', 'vigencia_meses')
    def _compute_validity_date(self):
        for rec in self:
            if not rec.exists():
                continue
            if rec.x_rental_start_date and rec.vigencia_meses:
                rec.validity_date = rec.x_rental_start_date + relativedelta(months=rec.vigencia_meses, days=-1) 
            else:
                rec.validity_date = False

    # ====== FIN BLOQUE: Vigencia de contrato ======
    
    def _check_active_contracts(self):
        for rec in self:
            scope = rec.ecoerp_scope
            if not rec.x_account_analytic_account_id or rec.x_custom_state == 'done':
                continue

            # Validación para contratos de PROPIETARIOS
            if scope == "owner":
                domain_owner = [
                    ('x_account_analytic_account_id', '=', rec.x_account_analytic_account_id.id),
                    ('ecoerp_scope', '=', scope),
                    ('x_custom_state', '!=', 'done'),
                    ('id', '!=', rec.id),
                ]
                active_owner_contracts = self.search(domain_owner)
                if active_owner_contracts:
                    raise ValidationError(
                        f"La propiedad {rec.x_account_analytic_account_id.display_name} "
                        f"ya tiene un contrato de propietario activo."
                    )

            # Validación para contratos de ARRENDATARIOS
            elif scope == "tenant" and rec.partner_id:
                domain_tenant = [
                    ('x_account_analytic_account_id', '=', rec.x_account_analytic_account_id.id),
                    ('partner_id', '=', rec.partner_id.id),
                    ('ecoerp_scope', '=', scope),
                    ('x_custom_state', '!=', 'done'),
                    ('id', '!=', rec.id),
                ]
                active_tenant_contracts = self.search(domain_tenant)
                if active_tenant_contracts:
                    raise ValidationError(
                        f"El arrendatario {rec.partner_id.display_name} ya tiene un contrato activo "
                        f"para la propiedad {rec.x_account_analytic_account_id.display_name}."
                    )
                    
    


    def _validate_owner_total(self):
        for order in self.filtered(lambda o: o.ecoerp_scope == 'owner'):
            total = sum(order.owner_responsibility_ids.mapped('percent') or [0.0])
            # precisión 2 decimales; ajusta si usas otra
            if order.owner_responsibility_ids and float_compare(total, 100.0, precision_digits=2) != 0:
                raise ValidationError(_("La suma de porcentajes debe ser 100%% (actual: %.2f).") % total)
            
    @api.depends('x_account_analytic_account_id', 'x_account_analytic_account_id.owner_partner_ids')
    def _compute_owner_candidates(self):
        Partner = self.env['res.partner']
        for o in self:
            if not o.exists():
                continue
            if o.x_account_analytic_account_id:
                o.owner_candidate_ids = o.x_account_analytic_account_id.owner_partner_ids
            else:
                # mostrar todos los propietarios cuando aún no hay propiedad
                #o.owner_candidate_ids = Partner.search([('is_property_owner', '=', True)])
                # SIN propiedad aún: todos los “posibles propietarios”
                o.owner_candidate_ids = Partner.search([
                    '|',
                    ('is_property_owner', '=', True),
                    ('category_id.name', 'ilike', 'Propietario'),
                ])
        
    @api.onchange('property_id')
    def _onchange_property_prefill_owner_resps(self):
        if self.ecoerp_scope != 'owner' or not self.property_id:
            return
        if self.owner_responsibility_ids:
            return
        lines = []
        for l in self.property_id.owner_line_ids.exists():
            lines.append((0, 0, {
                'owner_id': l.owner_id.id,
                'percent': l.participation_percent or 0.0,
                'subject_to_vat': l.iva or False,
                'is_main_payee': getattr(l, 'is_main_payee', False),
            }))
        if lines:
            self.owner_responsibility_ids = lines

    @api.constrains('date_owner_start','date_owner_end')
    def _check_dates(self):
        for s in self:
            if s.ecoerp_scope == 'owner' and s.date_owner_start and s.date_owner_end and s.date_owner_end < s.date_owner_start:
                raise ValidationError(_("La fecha fin debe ser posterior a la de inicio."))
    
    @api.constrains('date_owner_start', 'date_owner_end')
    def _check_owner_dates(self):
        for s in self:
            if s.ecoerp_scope == 'owner' and s.date_owner_start and s.date_owner_end and s.date_owner_end < s.date_owner_start:
                raise ValidationError(_("La fecha de terminación debe ser posterior a la de inicio."))

    @api.constrains('ecoerp_contract', 'x_account_analytic_account_id')
    def _check_x_account_required_for_ecoerp(self):
        for rec in self:
            if rec.ecoerp_contract and not rec.x_account_analytic_account_id:
                raise ValidationError(_("No ha asociado una propiedad al contrato."))    
    
    def copy(self, default=None):
        # Al duplicar, conservamos el valor del flag (para no “mover” contratos a Ventas normales)
        default = dict(default or {})
        default.setdefault('ecoerp_contract', self.ecoerp_contract)
        default.setdefault('ecoerp_scope', self.ecoerp_scope)
        return super().copy(default)
    
    @api.depends('contract_id', 'contract_id.x_custom_state')
    def _compute_x_custom_state(self):
        for order in self:
            if not order.exists():
                continue
            if order.contract_id:
                order.x_custom_state = order.contract_id.x_custom_state or 'draft'
            else:
                order.x_custom_state = 'draft'
    
    @api.depends('contract_id')
    def _compute_contract_sign_request_ids(self):
        SignRequest = self.env['sign.request'].sudo()
        for order in self:
            if not order.exists():
                continue
            reqs = SignRequest.search([('x_contract_id', '=', order.contract_id.id)]) if order.contract_id else SignRequest.browse()
            order.contract_sign_request_ids = reqs
            order.sign_request_count = len(reqs)
    
    def action_request_signature_from_order(self):
        """Botón de la pestaña: abre el asistente de firma del contrato."""
        self.ensure_one()
        if not self.contract_id:
            raise UserError(_("Esta solicitud no tiene contrato aún."))        
        return self.contract_id.action_request_signature()
    
    def _compute_signed_docs_count(self):
        SignRequest = self.env['sign.request'].sudo()
        for order in self:
            if not order.exists():
                continue
            if order.contract_id:
                order.signed_docs_count = SignRequest.search_count([
                    ('x_contract_id', '=', order.contract_id.id),  # tu M2O en sign.request
                    ('state', 'in', ['signed', 'completed']),      # usa el/los estados que valen en tu versión
                ])
            else:
                order.signed_docs_count = 0

    def action_view_signed_docs(self):
        self.ensure_one()
        if not self.contract_id:
            raise UserError(_("Primero asocia un contrato."))
        # intenta actions del módulo sign según versión
        for xmlid in ('sign.sign_request_action', 'sign.action_sign_requests'):
            action = self.env.ref(xmlid, raise_if_not_found=False)
            if action:
                action = action.sudo().read()[0]
                action['domain'] = [('x_contract_id', '=', self.contract_id.id)]
                # asegura view_mode válido en v17/18
                action['view_mode'] = action.get('view_mode') or 'list,form'
                action['views'] = [(v[0], 'list' if v[1] in ('tree', False) else v[1]) for v in action.get('views', [])]
                return action
        return {
            'type': 'ir.actions.act_window',
            'name': _("Solicitudes de firma"),
            'res_model': 'sign.request',
            'view_mode': 'list,form',
            'domain': [('x_contract_id', '=', self.contract_id.id)],
        }
    
    def _compute_contract_is_signed(self):
        for o in self:
            if not o.exists():
                continue
            r = o.contract_id
            o.contract_is_signed = bool(r and r.sign_request_id and r.sign_request_id.state == 'contract_signed')

    def action_open_contract(self):
        self.ensure_one()
        if not self.contract_id:
            self.contract_id = self.env['x.contract'].create({
                'sale_order_id': self.id,
                'partner_id': self.partner_id.id,
            })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'x.contract',
            'res_id': self.contract_id.id,
            'view_mode': 'form',
            'views': [(self.env.ref('industry_real_estate.view_x_contract_form').id, 'form')],
            'target': 'current',
        }
    
    @api.onchange('x_contract_template_id')
    def _onchange_x_contract_template_id(self):
        if not self.x_contract_template_id:
            self._clear_contract_content()
            return
            
        template = self.x_contract_template_id
        
        # 1. Copiar metadatos
        self.contract_title = template.contract_title
        # self.contract_preface = template.preface
        
        # 2. Para onchange, solo preparamos los datos - las cláusulas se crearán al guardar
        self._prepare_clauses_from_template(template)
        

    def _clear_contract_content(self):
        """Limpiar contenido del contrato"""
        self.contract_title = False
        # self.contract_preface = False
        self.sale_clause_line_ids = [(5, 0, 0)]
        self.clause_var_ids = [(5, 0, 0)]

    def _prepare_clauses_from_template(self, template):
        """Preparar cláusulas desde plantilla para onchange (sin crear en BD)"""
        clause_data = []
        
        for catalog_clause in template.clause_line_ids.sorted('sequence'):
            # Para onchange, crear objetos NewId que se resuelven al guardar
            clause_data.append((0, 0, {
                'name': catalog_clause.name,
                'title': catalog_clause.title,
                'description': catalog_clause.description,
                'ident': catalog_clause.ident,
                'sequence': catalog_clause.sequence,
                'is_master': False,                    # ← INSTANCIA DE CONTRATO
                'master_clause_id': catalog_clause.id, # ← Referencia al catálogo
                'parent_clause_line_id': False,       # Se establecerá después
                # sale_order_id se asignará automáticamente por la relación One2many
            }))
        
        # Asignar datos para vista previa
        self.sale_clause_line_ids = [(5, 0, 0)] + clause_data

    def _create_clauses_from_template(self, template):
        """Crear instancias de cláusulas específicas del contrato desde plantilla"""
        clause_data = []
        
        for catalog_clause in template.clause_line_ids.sorted('sequence'):
            clause_data.append((0, 0, {
                'name': catalog_clause.name,
                'title': catalog_clause.title,
                'description': catalog_clause.description,
                'ident': catalog_clause.ident,
                'sequence': catalog_clause.sequence,
                'is_master': False,                    # ← INSTANCIA DE CONTRATO
                'sale_order_id': self.id,             # ← Pertenece al contrato
                'template_id': False,                 # ← Ya no es de plantilla
                'master_clause_id': catalog_clause.id, # ← Referencia al catálogo
                'parent_clause_line_id': False,       # Se establecerá después
            }))
        
        # Crear todas las cláusulas (variables se crean automáticamente)
        self.sale_clause_line_ids = [(5, 0, 0)] + clause_data
        
        # Establecer relaciones padre-hijo para parágrafos
        self._establish_paragraph_relationships()

    def _establish_paragraph_relationships(self):
        """Establecer relaciones padre-hijo para parágrafos basándose en la plantilla"""
        if not self.x_contract_template_id:
            return
            
        # Mapear cláusulas master a cláusulas del contrato
        master_to_contract = {}
        for contract_clause in self.sale_clause_line_ids:
            if contract_clause.master_clause_id:
                master_to_contract[contract_clause.master_clause_id.id] = contract_clause
        
        # Establecer relaciones padre-hijo
        for contract_clause in self.sale_clause_line_ids:
            if contract_clause.ident == 'PARAGRAFO' and contract_clause.master_clause_id:
                # Buscar el padre en la plantilla
                template_parent = None
                for template_clause in self.x_contract_template_id.clause_line_ids:
                    if (template_clause.ident == 'PARAGRAFO' and 
                        template_clause.id == contract_clause.master_clause_id.id):
                        # Buscar la cláusula padre en la plantilla
                        for potential_parent in self.x_contract_template_id.clause_line_ids:
                            if (potential_parent.ident == 'CLAUSULA' and 
                                potential_parent.sequence < template_clause.sequence):
                                template_parent = potential_parent
                        break
                
                # Asignar el padre correspondiente en el contrato
                if template_parent and template_parent.id in master_to_contract:
                    contract_clause.parent_clause_line_id = master_to_contract[template_parent.id]

    @api.depends('x_custom_state')
    def _compute_can_see_delivery_tab(self):
        for record in self:
            if not record.exists():
                continue
            record.can_see_delivery_tab = record.x_custom_state not in ['draft', 'contract_signed', 'pending_delivery', 'delivered']


    @api.depends('x_custom_state')
    def _compute_can_see_reception_tab(self):
        for record in self:
            if not record.exists():
                continue
            record.can_see_reception_tab = record.x_custom_state not in ['pending_receipt', 'received']

    @api.depends(
        'sale_clause_line_ids.rendered_text',
        'sale_clause_line_ids.sequence',
        'clause_var_ids.value'
    )
    def _compute_rendered_clauses(self):
        """Renderizar contrato completo con variables sustituidas según nueva arquitectura"""
        for contract in self:
            if not contract.exists():
                continue
            if not contract.sale_clause_line_ids:
                contract.rendered_clauses = ""
                continue
                
            # Obtener diccionario de variables usando el método consistente
            variables_dict = contract.get_vars_dict()
            
            # Renderizar cada cláusula usando el nuevo método
            rendered_parts = []
            for clause in contract.sale_clause_line_ids.sorted('sequence'):
                rendered_text = contract._render_single_clause(clause, variables_dict)
                if rendered_text:
                    rendered_parts.append(rendered_text)
                    
            # _logger.info(f"ANEXOS: {contract.contract_annex_ids}")
            for annex in contract.contract_annex_ids.sorted('sequence'):
                block = annex._render_annex_block()
                if block:
                    rendered_parts.append(block)
                
            # Unir con saltos de línea - parágrafos van seguidos, cláusulas con más espacio
            final_text = ''.join(rendered_parts) 
            contract.rendered_clauses = final_text


    def recompute_paragraph_parents(self):
        """Asigna automáticamente los parágrafos a la cláusula precedente según el orden"""
        for order in self:
            lines = order.sale_clause_line_ids.sorted('sequence')
            last_clause = None
            for line in lines:
                if line.ident == 'CLAUSULA':
                    last_clause = line
                elif line.ident == 'PARAGRAFO':
                    if last_clause and line.parent_clause_line_id != last_clause:
                        line.parent_clause_line_id = last_clause
    
     
    def _organize_clause_hierarchy(self):
        """Ordena las cláusulas y párrafos por jerarquía"""
        
        lines = self.sale_clause_line_ids.sorted('sequence')
        organized = []
        last_clause = None
        
        for line in lines:
            if line.ident == 'CLAUSULA':
                last_clause = line
                organized.append({
                    'line': line,
                    'type': 'clausula',
                    'level': 0
                })
            elif line.ident == 'PARAGRAFO':
                if last_clause:
                    organized.append({
                        'line': line,
                        'type': 'paragrafo',
                        'level': 1,
                        'parent': last_clause
                    })
        
        return organized

    def _render_single_clause_legacy(self, line_data, vars_dict):
        """Renderiza una línea individual con su formato específico (método legacy)"""
        if not line_data or 'line' not in line_data:
            return ''
        
        line = line_data['line']
        if not line.exists():
            return ''

        # Renderizar el texto base
        rendered_text = line.render_template_with(vars_dict)
        if not rendered_text:
            return ''
        
        # Extraer solo el texto dentro de las etiquetas HTML
        text_content = re.sub(r'<[^>]+>', '', rendered_text).strip()
        
        # Construir el prefijo según el tipo
        prefix_parts = []
        
        # Agregar tipo (CLAUSULA/PARAGRAFO)
        if line.ident:
            if line.ident == 'PARAGRAFO' and not line.auto_number:
                prefix_parts.append('PARAGRAFO:')
            else:
                prefix_parts.append(line.ident)
        
        # Agregar numeración automática (calculada por clause_line._compute_auto_number)
        if line.auto_number:
            prefix_parts.append(line.auto_number + ':')
        
        # Agregar título de la cláusula si existe
        if hasattr(line, 'title') and line.title and line.ident != 'PARAGRAFO':
            prefix_parts.append(line.title + ' -. ')
        
        # Construir el prefijo final
        prefix = ' '.join(prefix_parts)
        
        # Retornar el texto completo sin etiquetas de bloque
        if prefix:
            return f"<strong>{prefix}</strong> {text_content}"
        else:
            return text_content
    
    def get_vars_context(self):
        """Obtiene contexto de variables para renderizado (método legacy)"""
        contract_clauses = self.env["clause.var"].search([ ("contract_id", "=", self.id) ])
        return {var.key: var.value for var in contract_clauses}


    @api.onchange('sale_clause_line_ids')
    def _onchange_sale_clause_line_ids(self):
        self._generate_clause_vars()


    def _generate_clause_vars(self):
        """Crear/limpiar clause_var_ids y DEVOLVER SIEMPRE la lista de variables (únicas)."""
        all_results = {}  # order.id -> set(str)

        for order in self:
            try:
                all_vars = set()

                if isinstance(order.id, models.NewId):
                    # ----- REGISTRO TEMPORAL -----
                    for line in order.sale_clause_line_ids:
                        vars_list = (line.get_vars_list() or [])
                        all_vars.update(vars_list)

                    # refresca one2many temporal
                    order.clause_var_ids = [(5, 0, 0)]
                    temp_vars = [(0, 0, {'key': v, 'value': ''}) for v in sorted(all_vars)]
                    order.clause_var_ids = temp_vars

                    # limpiar obsoletas temporales (por si acaso)
                    current_vars = set(all_vars)
                    existing_vars = {v.key for v in order.clause_var_ids if v.key}
                    obsolete = existing_vars - current_vars
                    if obsolete:
                        order.clause_var_ids = order.clause_var_ids.filtered(lambda v: v.key not in obsolete)

                else:
                    # ----- REGISTRO PERSISTIDO -----
                    for line in order.sale_clause_line_ids:
                        for var_name in (line.get_vars_list() or []):
                            all_vars.add(var_name)
                            exists = order.clause_var_ids.filtered(lambda v: v.key == var_name and v.clause_id.id == line.id)
                            if not exists:
                                self.env['clause.var'].create({
                                    'key': var_name,
                                    'value': '',
                                    'contract_id': order.id,
                                    'clause_id': line.id,
                                })

                    # limpiar obsoletas en BD
                    current_clause_ids = set(order.sale_clause_line_ids.ids)
                    valid_pairs = {(line.id, vn) for line in order.sale_clause_line_ids for vn in (line.get_vars_list() or [])}

                    to_remove = []
                    for var in order.clause_var_ids:
                        if (var.clause_id.id not in current_clause_ids) or ((var.clause_id.id, var.key) not in valid_pairs):
                            to_remove.append(var.id)
                    if to_remove:
                        self.env['clause.var'].browse(to_remove).unlink()

                # guarda el set para este order
                all_results[order.id] = all_vars

            except Exception:
                _logger.exception("Falló _generate_clause_vars() en SO %s", order.id)
                all_results[order.id] = set()

        # DEVUELVE lista para soportar los sitios donde se hace set(...)
        # Si es recordset de 1, devuelve lista simple; si es múltiple, devuelve dict por compatibilidad
        if len(self) == 1:
            return sorted(all_results[self.id])
        return {oid: sorted(vals) for oid, vals in all_results.items()}
        

    def get_vars_dict(self):
        self.ensure_one()
        # Para registros temporales y persistidos, usar las variables disponibles
        vars = self.clause_var_ids  # One2many 'clause.var' con 'contract_id' = self.id
        #vars_dict = {var.key: var.value or f"[{var.key}]" for var in vars if var.key}
        vars_dict = {var.key: var.value or "" for var in vars if var.key}
        return vars_dict
    

    def action_to_pending_delivery(self):
        # self.write({'x_custom_state': 'pending_delivery'})
        for order in self:
            if not order.contract_id:
                raise UserError(_("No se evidencia documento de convenio para entrega."))
            order.contract_id.with_context(new_state='pending_delivery').action_change_state()
        
    def action_to_contract_signed(self):
        self.ensure_one()
        contract = self.contract_id
        if not contract:
            raise UserError(_("No se encontró un contrato asociado."))

        target = 'contract_signed'
        # primero intentamos validar; si falta documento, abrimos el asistente
        partner = self.partner_id
        partner_lessor = self.partner_lessor_id
        guarant = self.x_guarant_partner_id
        signers = [partner, partner_lessor] + list(guarant)
        try:
            contract._set_property_availability(available=True)
            return contract.with_context(new_state=target).action_change_state()
        except UserError as e:
            # Cualquier otro UserError también te sirve para abrir el asistente            
            return contract.with_context(target_state=target).action_request_signature(target_state=None, signers=signers)

    def action_to_delivered(self):
        for order in self:
            if not order.contract_id:
                raise UserError(_("No hay un documento de paz y salvo hacia el arrendatario ."))
            has_lines = bool(order.x_reception_card_line_ids)
            if not has_lines:
                raise UserError("No existe inventario en la propiedad, debe tener al menos un producto asociado para poder continuar")
            else:
                # self.write({'x_custom_state': 'delivered'})
                order.contract_id.with_context(new_state='delivered').action_change_state()
        

    def action_to_pending_receipt(self):
        for order in self:
            if not order.contract_id:
                raise UserError(_("No hay un documento de convenio para recepción."))
            has_lines = bool(order.x_reception_card_line_ids)
            if not has_lines:
                raise UserError("No existe inventario en la propiedad, debe tener al menos un producto asociado para poder continuar")
            else:
                # self.write({'x_custom_state': 'pending_receipt'})
                order.contract_id.with_context(new_state='pending_receipt').action_change_state()

    def action_to_received(self):
        for order in self:  
            if not order.contract_id:
                raise UserError(_("No hay un documento de paz y salvo del arrendatario."))          
            # Filtrar líneas de recepción que no estén validadas
            pending = order.x_reception_card_line_ids.filtered(lambda l: not l.validated)
            has_lines = bool(order.x_reception_card_line_ids)
            # si existen items sin validar, sacará alerta
            if pending:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'confirm.reception.wizard',
                    'view_mode': 'form',
                    'view_id': self.env.ref('industry_real_estate.view_confirm_reception_wizard_form').id,
                    'target': 'new',
                    'context': {
                        'default_order_id': order.id,
                    }
                }

            elif has_lines: # si todo está bien, ingresa acá
                # order.write({'x_custom_state': 'received'})
                order.contract_id.with_context(new_state='received').action_change_state()
            else:# sino, es porque no hay resultados de ningún tipo
                raise UserError("No existe inventario en la propiedad, debe tener al menos un producto asociado para poder continuar")
        # Si todo está validado, cambia el estado
        # Esta validación se migró al modelo ConfirmReceptionWizard.
        # order.write({'x_custom_state': 'received'})

    def action_to_done(self):
        # self.write({'x_custom_state': 'done'})
        for order in self:  
            if not order.contract_id:
                raise UserError(_("No existe documento anexo para finalización de contrato."))  
            order.contract_id.with_context(new_state='done').action_change_state()

    def action_reset_draft(self):
        self.ensure_one()
        if not self.contract_id:
            raise UserError(_("No existe documento de evidencia para reestablecer este contrato."))
        # Cambia el contrato a 'draft'
        self.contract_id.with_context(new_state='draft').action_change_state()
        # Recarga la vista del pedido
        # return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_otro_si(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nuevo Otrosí',
            'res_model': 'contract.annex',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_sale_order_id': self.id,
                'default_annex_type': 'otrosi',
            },
        }

    def action_create_transaccion(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nuevo Contrato de Transacción',
            'res_model': 'contract.annex',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_sale_order_id': self.id,
                'default_annex_type': 'transaccion',
            },
        }

    def _render_single_clause(self, clause, variables_dict):
        """Renderizar una cláusula individual según la nueva arquitectura"""
        
        # Calcular numeración automática directamente (sin usar campo computed)
        header = ""
        if clause.ident == 'CLAUSULA':
            auto_number = clause.get_clausula_number_for_context(sale_order=self, template=None)
            if auto_number and clause.title:
                # Formato: CLAUSULA PRIMERA: OBJETO DEL CONTRATO -.
                header = f"<strong>CLAUSULA {auto_number}: {clause.title.upper()} -.</strong> "
            elif auto_number:
                header = f"<strong>CLAUSULA {auto_number}:</strong> "
        elif clause.ident == 'PARAGRAFO':
            auto_number = clause.get_paragrafo_number_for_context(sale_order=self, template=None)
            if auto_number:
                # Formato: PARAGRAFO 1: (con numeración cuando hay múltiples)
                header = f"<strong>PARAGRAFO {auto_number}:</strong> "
            else:
                # Formato: PARAGRAFO: (sin numeración cuando hay solo uno)
                header = f"<strong>PARAGRAFO:</strong> "
        
        # Obtener contenido (propio o del maestro)
        content = clause.description or ""
        if not content and clause.master_clause_id:
            content = clause.master_clause_id.description or ""
        
        # Limpiar etiquetas HTML del contenido para que sea texto plano
        clean_content = re.sub(r'<[^>]+>', '', content).strip()
        
        # Sustituir variables en el contenido
        def replace_var(match):
            var_name = match.group(1)
            #return variables_dict.get(var_name, f"[VAR_{var_name}_NO_DEFINIDA]")  # Placeholder visible si no existe
            return variables_dict.get(var_name, "")  # Si no existe, deja vacío
        
        pattern = re.compile(r'\$\{([A-Z][A-Z0-9_]*)\}')
        rendered_content = pattern.sub(replace_var, clean_content)
        
        # Combinar header y contenido en la misma línea, todo como texto plano
        return f"{header}{rendered_content}"
        
          
    @api.depends('x_custom_state')# dependemos de los valores que se van a mostrar en tarjeta
    def _compute_can_add_inventory(self):
        for record in self:
            if not record.exists():
                continue
            record.can_add_inventory = False # no puede crear inventario por defecto
            if record.x_custom_state in ['draft', 'contract_signed', 'pending_delivery']:
                record.can_add_inventory = True # puede crear inventario
                
    # @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            # Solo aplica para formularios (donde está tu kanban)
            for record in self:
                res['fields']['can_add_inventory']['context'] = {
                    'can_add_inventory': record.can_add_inventory
                }
        return res
    
    @api.onchange('property_id', 'ecoerp_scope')
    def _onchange_property_prefill_owners(self):
        """Al cambiar Propiedad/alcance:
        - Prellena responsabilidades desde la propiedad
        - Y deja la propiedad alineada con lo que ya tenga el contrato (si hubiera)
        """
        for o in self:
            if o.ecoerp_scope != 'owner' or not o.property_id:
                continue

            acc = o.property_id.sudo()

            # 1) Mapas por owner_id en ambos lados
            prop_map = {l.owner_id.id: l for l in acc.owner_line_ids.exists()}
            ord_map  = {r.owner_id.id: r for r in o.owner_responsibility_ids if r.owner_id}

            # 2) Conjunto final de propietarios
            owner_ids = set(prop_map) | set(ord_map)

            # 3) Comandos para refrescar las líneas del contrato (limpio + recreo)
            cmds = [(5, 0, 0)]
            for oid in owner_ids:
                pl = prop_map.get(oid)  # línea en propiedad
                rl = ord_map.get(oid)   # línea en contrato
                print("PL", pl)
                print("RL", rl)
                # Toma valores: prioriza contrato si ya tenía algo, si no, propiedad
                pct  = (rl and rl.percent) or (pl and pl.participation_percent) or 0.0
                iva  = bool((rl and rl.subject_to_vat) or (pl and pl.iva) or False)
                main = bool((rl and rl.is_main_payee) or (getattr(pl, 'is_main_payee', False)))

                cmds.append((0, 0, {
                    'owner_id': oid,
                    'percent': pct,
                    'subject_to_vat': iva,
                    'is_copropietario': pct < 100.0,
                    'is_main_payee': main,
                }))

                # 4) Asegurar que la PROPIEDAD refleje lo mismo (crear/actualizar)
                print("PAYEE", pl.is_main_payee)
                if not pl:
                    # crea línea de propietario en la propiedad
                    self.env['account.analytic.account.owner.line'].with_context(skip_owner_sync=True).create(
                        {
                            'analytic_account_id': acc.id,
                            'owner_id': oid,
                            'participation_percent': pct,
                            'iva': iva,
                            'is_main_payee': main,
                        }
                    )
                else:
                    vals_upd = {}
                    if (pl.participation_percent or 0.0) != pct:
                        vals_upd['participation_percent'] = pct
                    if bool(pl.iva) != iva:
                        vals_upd['iva'] = iva
                    if bool(pl.is_main_payee) != main:
                        vals_upd['is_main_payee'] = main
                    if vals_upd:
                        pl.with_context(skip_owner_sync=True).write(vals_upd)

            # 5) Aplicar snapshot al contrato
            o.owner_responsibility_ids = cmds

            # 6) Si no hay partner principal en la orden, usa el primero
            if not o.partner_id and owner_ids:
                o.partner_id = next(iter(owner_ids))
    
    @api.depends('date_owner_start','date_owner_end','property_id')
    def _compute_owner_base(self):
        """Esqueleto: suma de ingresos en rango (ajusta a tu lógica)."""
        for o in self:
            if not o.exists():
                continue
            o.amount_owner_base = 0.0
            if o.ecoerp_scope != 'owner' or not (o.date_owner_start and o.date_owner_end):
                continue
            # Aquí puedes filtrar por analítica de la propiedad si la usas en facturas
            lines = self.env['account.move.line'].search([
                ('move_id.move_type','=','out_invoice'),
                ('move_id.state','=','posted'),
                ('date','>=',o.date_owner_start),
                ('date','<=',o.date_owner_end),
            ])
            o.amount_owner_base = sum(lines.mapped('price_subtotal')) 

    def _get_ecoerp_settings(self):
        IC = self.env['ir.config_parameter'].sudo()
        admin_pct = float(IC.get_param('eco_erp.default_admin_percent', default=10.0))
        product_canon = self.env['product.product'].browse(int(IC.get_param('eco_erp.product_canon_id') or 0))
        product_owner = self.env['product.product'].browse(int(IC.get_param('eco_erp.product_owner_payment_id') or 0))
        return admin_pct, product_canon, product_owner
    
    def _get_vars_contables_contrato(self, date=None, contractXorder=None):
            """Obtiene variables contables del contrato ECOERP"""
            contract = self
            #variables del contrato
            vars_contracts = contract.env['clause.var']
            uso_destino = vars_contracts.search([('contract_id', '=', contract.id), ('key', '=', 'SOLICITUD_DESTINO_INMUEBLE')], limit=1)
            canon = vars_contracts.search([('contract_id', '=', contract.id), ('key', '=', 'CONTRATO_CANON')], limit=1)
            # variables del sistema
            company = contract.company_id or self.env.company
            tenant = contract.partner_id
            property_account = contract.x_account_analytic_account_id
            rent_amount = float(canon.value or 0.0)
            admin_pct, product_canon, product_owner = contract._get_ecoerp_settings()
            vigencia = contract.vigencia_meses
            termino_pago = contract.payment_term_id
            contrato_inicio = contract.x_rental_start_date
            contrato_fin = contract.validity_date
            ipc = company.porcentaje_ipc or 0.0
            porcentaje_adicional_ipc = 0.0
            porcentaje_cobros_adicionales = 0.0
            cobro_adicional_ipc = contract.cobro_adicional_ipc_re
            cobro_comision_inicial = contract.cobro_comision_inicial
            cobros_adicionales = contract.cobro_adicional
            cobro_papeleria = contract.cobro_papeleria
            porcentaje_comision_inicial = 0.0
            monto_cobros_adicionales = 0.0
            monto_adicional_paleria = 0.0
            usura = company.tasa_usura or 0.0
            dias_gracia_mora = getattr(contract.company_id, 'dias_gracia_mora', 3) or 3
            porcentaje_mora  = getattr(contract.company_id, 'porcentaje_mora', 0.0) or 0.0
            apply_ipc = False
            
            effective_date = date or fields.Date.context_today(self)
            # Busca en x.contract campos comunes; si no, intenta variable CONTRATO_INICIO; si no, usa date_order; si no, hoy
            base_date = False
            for fname in ('start_date', 'date_start'):
                if hasattr(contractXorder, fname) and getattr(contractXorder, fname):
                    base_date = getattr(contractXorder, fname)
                    break

            if not base_date:
                # Intentar desde variable
                start_var = contrato_inicio
                if contrato_inicio:
                    try:
                        base_date = fields.Date.to_date(contrato_inicio)
                    except Exception:
                        base_date = False

            if not base_date:
                base_date = contract.date_order or fields.Date.context_today(self)
            # Calcular fecha de primer aniversario
            if relativedelta:
                anniv_date = base_date + relativedelta(years=1)
            else:
                # Fallback simple si no está dateutil (suma 365 días)
                anniv_date = fields.Date.to_date(base_date) + dt.timedelta(days=365)
            anniv_date_str = fields.Date.to_string(anniv_date)
            if uso_destino == 'commercial' and cobro_adicional_ipc:
                apply_ipc = fields.Date.to_date(effective_date) >= fields.Date.to_date(anniv_date)  
                
            if cobro_comision_inicial:
                porcentaje_comision_inicial = contract.porcentaje_comision_inicial or 0.0     
            
            if cobros_adicionales:
                porcentaje_cobros_adicionales = company.porcentaje_cobros_adicionales or 0.0 
                monto_cobros_adicionales = contract.monto_cobros_adicionales or 0.0  
            
            if cobro_papeleria:
                monto_adicional_paleria = contract.monto_adicional_paleria or 0.0
                
            if apply_ipc:
                porcentaje_adicional_ipc = contract.porcentaje_adicional_ipc or 0.0 
            
            base_original = float(rent_amount or 0.0)
            currency = contract.currency_id or contract.company_id.currency_id
            
            return {
                'tenant': tenant or False,
                'property_account': property_account or False,
                'rent_amount': rent_amount or 0.0,
                'admin_pct': admin_pct or 0.0,
                'product_canon': product_canon or False,
                'product_owner': product_owner or False,
                'vigencia': vigencia or 0,
                'termino_pago': termino_pago or False,
                'contrato_inicio': contrato_inicio or False,
                'contrato_fin': contrato_fin or False,
                'ipc': ipc or 0.0,
                'porcentaje_adicional_ipc': porcentaje_adicional_ipc or 0.0,
                'porcentaje_cobros_adicionales': porcentaje_cobros_adicionales or 0.0,
                'porcentaje_comision_inicial': porcentaje_comision_inicial or 0.0,
                'monto_cobros_adicionales': monto_cobros_adicionales or 0.0,
                'monto_adicional_paleria': monto_adicional_paleria or 0.0,
                'company': company or False,
                'usura': usura or 0.0,
                'apply_ipc': apply_ipc or False,
                'base_original': base_original or 0.0,
                'currency': currency or False,
                'delta': 0.0,
                'base_date': base_date or False,
                'anniv_date':anniv_date or False,
                'anniv_date_str': anniv_date_str or False,
                'effective_date': effective_date or False,
                'dias_gracia_mora': dias_gracia_mora or 0,
                'porcentaje_mora': porcentaje_mora or 0.0,
                'vars_contracts': vars_contracts,                
            }
        
    def _sync_contract_vars_panel(self):
        for order in self:
            codes = order._generate_clause_vars() or []
            desired = set(codes)   # contrato + anexos
            existing_by_name = {l.key: l for l in order.clause_var_ids}

            # Crear las que faltan
            to_create = [v for v in desired if v not in existing_by_name]
            if to_create:
                order.clause_var_ids = [(0, 0, {'key': v}) for v in to_create] + []
            # Eliminar únicamente las que ya no existen en el texto
            to_delete = order.clause_var_ids.filtered(lambda l: l.key not in desired)
            if to_delete:
                to_delete.unlink()
        
    @api.model_create_multi
    def create(self, vals_list):
        # (A) Capturar inputs del usuario en clause_var_ids
        #     • con_key:  dict key->value
        #     • sin_key:  lista de valores en el orden que el usuario los digitó
        user_inputs = []  # paralelo a vals_list
        for vals in vals_list:
            with_key = {}
            without_key = []
            cleaned_cmds = []
            for cmd in (vals.get('clause_var_ids') or []):
                if cmd and cmd[0] == 0 and len(cmd) >= 3 and cmd[2] is not None:
                    k = (cmd[2].get('key') or '').strip()
                    v = cmd[2].get('value') or ''
                    if k:
                        with_key[k] = v
                        # dejamos pasar el comando original (no lo tocamos)
                        cleaned_cmds.append(cmd)
                    else:
                        # guardamos el valor, pero NO creamos una clause.var sin key en super()
                        without_key.append(v)
                else:
                    cleaned_cmds.append(cmd)
            # reemplazamos por los comandos limpios (sin los (0,0) sin key)
            vals['clause_var_ids'] = cleaned_cmds
            user_inputs.append({'with_key': with_key, 'without_key': without_key})

        # === (1) ECOERP flags desde contexto (tu lógica intacta) ===
        skip = self.env.context.get('is_order_flag')
        ctx_flag = False if skip else self.env.context.get('default_ecoerp_contract', None)
        ctx_scope = self.env.context.get('default_ecoerp_scope')
        for vals in vals_list:
            if ctx_flag is not None and 'ecoerp_contract' not in vals:
                vals['ecoerp_contract'] = bool(ctx_flag)
            if ctx_scope and 'ecoerp_scope' not in vals:
                vals['ecoerp_scope'] = ctx_scope

        # === (2) SUPER con guardias ===
        orders = super(SaleOrder, self.with_context(
            skip_preview_attachment=True,
            defer_sync_vars=True,
        )).create(vals_list)
        
        # orders._sync_dates_from_start()

        # === (3) Validaciones (intactas) ===
        try:
            orders._validate_owner_total()
        except Exception:
            _logger.exception("Fallo _validate_owner_total() en create")

        try:
            orders._check_active_contracts()
        except Exception:
            _logger.exception("Fallo _check_active_contracts() en create")

        # === (4) Contrato y plantilla firma (intacto) ===
        Contract = self.env['x.contract']
        sign_template = self.env['sign.template'].search([('name', '=', 'Contrato de Arrendamiento')], limit=1)
        for order in orders:
            if not getattr(order, 'contract_id', False):
                order.contract_id = Contract.create({
                    'sale_order_id': order.id,
                    'sign_template_id': sign_template.id if sign_template else False,
                })

        # === (5) Generar variables desde cláusulas (asegura keys en BD) ===
        for order in orders:
            try:
                order.with_context(**{CTX_KEY: True})._generate_clause_vars()
            except Exception:
                _logger.exception("Fallo _generate_clause_vars() en create de %s", order.name)

        # === (6) Aplicar valores del usuario ===
        ClauseVar = self.env['clause.var'].sudo()
        for order, ui in zip(orders, user_inputs):
            # 6.1) Con key: escribir directo en esa variable
            for k, v in (ui.get('with_key') or {}).items():
                try:
                    var = ClauseVar.search([('contract_id', '=', order.id), ('key', '=', k)], limit=1)
                    if var:
                        var.with_context(**{CTX_KEY: True}).write({'value': v or ''})
                    else:
                        # si no existe (poco probable), créala suelta
                        ClauseVar.with_context(**{CTX_KEY: True}).create({
                            'contract_id': order.id,
                            'key': k,
                            'value': v or '',
                        })
                except Exception:
                    _logger.exception("Fallo aplicando valor con key '%s' en %s", k, order.name)

            # 6.2) Sin key: repartir en las primeras variables VACÍAS (no pisamos nada)
            no_key_values = [v for v in (ui.get('without_key') or []) if (v or '').strip() != '']
            if no_key_values:
                try:
                    empty_vars = ClauseVar.search([
                        ('contract_id', '=', order.id),
                        ('value', 'in', [False, ''])
                    ], order='id asc')
                    for v, var in zip(no_key_values, empty_vars):
                        var.with_context(**{CTX_KEY: True}).write({'value': v})
                except Exception:
                    _logger.exception("Fallo asignando valores sin key en %s", order.name)

        # === (7) Completar automáticas SOLO donde esté vacío (no destructivo) ===
        for order in orders:
            try:
                order._fill_fixed_clause_vars()
            except Exception:
                _logger.exception("Fallo _fill_fixed_clause_vars() en create de %s", order.name)

        # === (8) Sincronizar panel (no destructivo) ===
        for order in orders:
            try:
                order._sync_contract_vars_panel()
            except Exception:
                _logger.exception("Fallo al sincronizar panel en create() de %s", order.name)

        # === (9) Flush + invalidate + compute ANTES del primer PDF ===
        for order in orders:
            try:
                order.env.cr.flush()
                order.invalidate_recordset(['rendered_clauses'])
                # fuerza compute para el primer render
                order._compute_rendered_clauses()
            except Exception:
                _logger.exception("Fallo flush/invalidate/compute previo a PDF en %s", order.name)

        # === (10) Generar y adjuntar PDF UNA sola vez por request ===
        ctx_once = {_PREVIEW_ONCE_KEY: True, _PREVIEW_CTX_FLAG: False}
        for order in orders:
            try:
                order.with_context(**ctx_once).action_update_contract_preview_pdf(html_override=None)
            except Exception:
                _logger.exception("Fallo al generar/adjuntar preview en create() para %s", order.name)

        return orders





    # ---- WRITE ÚNICO (fusionado) ----
    def write(self, vals):
        """
        ÚNICO write() consolidado para sale.order:
        - (CAMBIO) Pre-genera keys de variables si el cliente envía clause_var_ids.
        - NO descarta (0,0,{...}) sin 'key' (menos invasivo).
        - Mantiene tus validaciones y la generación de PDF como ya la tienes.
        """
        
        """ if 'x_rental_start_date' in vals:
            self._sync_dates_from_start() """
            
            
        # 0) Guardia: si venimos desde escritura interna de variables, no disparamos nada más.
        if self.env.context.get(CTX_KEY):
            return super(SaleOrder, self).write(vals)

        # 1) (CAMBIO) Si el cliente manda clause_var_ids, asegúrate de que existan las keys
        #    antes de aplicar los comandos del cliente (evita que se "pierdan" valores).
        if 'clause_var_ids' in vals:
            try:
                # Usamos CTX_KEY para que _generate_clause_vars no re-dispare write recursivo
                self.with_context(**{CTX_KEY: True})._generate_clause_vars()
            except Exception:
                _logger.exception("No se pudo pre-generar variables antes del write")

        # 2) (SIN CAMBIO) Llama a super con guardias para evitar recursión/sync prematuro
        res = super(SaleOrder, self.with_context(
            **{
                _PREVIEW_CTX_FLAG: True,   # no generar preview dentro del stack de super()
                'defer_sync_vars': True,   # evita sync de vars desde clause_line en mitad del write
            }
        )).write(vals)

        # 3) (SIN CAMBIO) Validaciones de negocio
        try:
            self._check_active_contracts()
        except Exception:
            _logger.exception("Fallo _check_active_contracts() en write")

        if 'owner_responsibility_ids' in vals or self.env.context.get('force_owner_total_check'):
            try:
                self._validate_owner_total()
            except Exception:
                _logger.exception("Fallo _validate_owner_total() en write")

        for order in self:
            if getattr(order, 'x_custom_state', 'draft') == 'draft' and 'x_reception_card_line_ids' in vals:
                raise UserError("No se pueden agregar recepciones mientras el contrato esté en estado 'Borrador'.")

        # 4) (SIN CAMBIO) Recompute jerarquía/variables si cambian las líneas de cláusulas
        if 'sale_clause_line_ids' in vals:
            for order in self:
                try:
                    order.recompute_paragraph_parents()
                    if hasattr(order, '_generate_clause_vars'):
                        order._generate_clause_vars()
                except Exception:
                    _logger.exception("Falló recompute jerarquía/_generate_clause_vars() en %s", order.name)
            self.invalidate_recordset(['rendered_clauses'])

        # 5) (SIN CAMBIO) Si cambian variables, forzar recomputación del render
        # if 'clause_var_ids' in vals:
        #     self.invalidate_recordset(['rendered_clauses'])
            
        try:
            # Si tocaron variables, intenta sincronizar (no pisa valores existentes)
            if 'clause_var_ids' in vals:
                # Completa CONTRATO_CANON_LETRAS si está vacío
                self._sync_canon_letras()

                # ✅ Nada de flush global. Solo recomputa el HTML del contrato.
                self.invalidate_recordset(['rendered_clauses'])

                # (Opcional) Si tu versión exige forzar el compute en caliente:
                # self._compute_rendered_clauses()
        except Exception:
            _logger.exception("Sync canon->letras post-write falló")
    

        # 6) (SIN CAMBIO) Autocompletar variables fijas cuando cambian campos clave (no destructivo)
        if FIELDS_PREVIEW_AFFECT.intersection(vals.keys()):
            try:
                self._fill_fixed_clause_vars()
            except Exception:
                _logger.exception("Fallo _fill_fixed_clause_vars() en write")

        # 7) (SIN CAMBIO) Sincronizar panel (post-write)
        for order in self:
            try:
                order._sync_contract_vars_panel()
            except Exception:
                _logger.exception("Fallo al sincronizar panel en write() de %s", order.name)

        # 7.5) (SIN CAMBIO) Refresco previo a PDF para garantizar primer render correcto en cambios masivos
        if FIELDS_PREVIEW_AFFECT.intersection(vals.keys()):
            for order in self:
                try:
                    # Re-generar listado de variables desde el texto (sin borrar manuales)
                    order.with_context(**{CTX_KEY: True})._generate_clause_vars()
                    # Completar automáticas solo si están vacías
                    order._fill_fixed_clause_vars()
                    # Sincronizar panel
                    order._sync_contract_vars_panel()
                    # Flush + invalidate para que rendered_clauses lea lo último
                    order.env.cr.flush()
                    order.invalidate_recordset(['rendered_clauses'])
                except Exception:
                    _logger.exception("Refresco previo a PDF falló en write() para %s", order.name)

        # 8) (SIN CAMBIO) Generar/adjuntar PDF (una vez por request)
        if FIELDS_PREVIEW_AFFECT.intersection(vals.keys()) and not self.env.context.get(_PREVIEW_ONCE_KEY):
            ctx_once = {
                _PREVIEW_ONCE_KEY: True,   # marca que ya se generó en este request
                _PREVIEW_CTX_FLAG: False,  # no saltar por contexto
            }
            for order in self:
                try:
                    order.with_context(**ctx_once).action_update_contract_preview_pdf(html_override=None)
                except Exception:
                    _logger.exception("Fallo al generar/adjuntar preview en write() para %s", order.name)

        return res



    #modificacion anexos
    def action_open_add_annex_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Agregar anexos'),
            'res_model': 'contract.annex',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,   # <-- sin active_id
            },
        }
    
    def action_add_annex_clauses(self, annex_ids):
        """Agregar anexos como cláusulas aisladas al contrato (sale.order)."""
        self.ensure_one()
        if not annex_ids:
            return

        Annex = self.env['contract.annex']
        ClauseLine = self.env['clause.line']
        ClauseVar = self.env['clause.var']

        annexes = Annex.browse(annex_ids).exists()
        if not annexes:
            raise UserError(_("No se encontraron anexos válidos."))

        for annex in annexes:
            # 1) Crear la línea de cláusula “aislada”
            line_vals = self._prepare_clause_line_vals_from_annex(annex)
            clause_line = ClauseLine.create(line_vals)

            # 2) Crear variables derivadas del anexo (si aplica)
            var_vals_list = self._prepare_clause_var_vals_from_annex(annex, clause_line)
            if var_vals_list:
                # asegura source='annex' en todas
                for vv in var_vals_list:
                    vv.setdefault('source', 'annex')
                    vv.setdefault('annex_id', annex.id)
                    vv.setdefault('order_id', self.id)
                ClauseVar.create(var_vals_list)

        # Devuelve una acción a la vista del pedido (opcional)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.id,
        }
    
    def _prepare_clause_line_vals_from_annex(self, annex):
        """Mapeo mínimo desde contract.annex -> clause.line (aislado)."""
        self.ensure_one()
        return {
            'order_id': self.id,
            'name': annex.name,              # o título del anexo
            'body': annex.body_html or annex.body_text,  # según tu modelo
            'sequence': annex.sequence or 999,
            'source': 'annex',
            'annex_id': annex.id,
            'template_id': False,            # <-- clave: no atado a plantilla
        }
        
    def _prepare_clause_var_vals_from_annex(self, annex, clause_line):
        """Si el anexo define variables, mapéalas a clause.var."""
        # Adapta a tu estructura de variables en contract.annex
        var_vals = []
        for av in annex.variable_ids:  # ej. contract.annex.variable
            var_vals.append({
                'order_id': self.id,
                'clause_line_id': clause_line.id,
                'key': av.key,
                'value': av.default_value or '',
                'source': 'annex',
                'annex_id': annex.id,
            })
        return var_vals
    
    @api.model
    def _cron_auto_confirm_contracts(self, limit=500):
        today = fields.Date.context_today(self)

        # 1) Confirmables: llegaron a su fecha de inicio y NO están “vencidas” por incremento
        confirm_domain = [
            ('state', 'in', ('draft', 'sent')),
            ('x_rental_start_date', '!=', False),
            ('x_rental_start_date', '<=', today),
            # '|', ('date_increment', '=', False), ('date_increment', '>=', today),
        ]
        orders_to_confirm = self.search(confirm_domain, limit=limit)
        if not orders_to_confirm:
            return True
        
        term_immediate = self.env.ref('account.account_payment_term_immediate', raise_if_not_found=False)

        for so in orders_to_confirm:
            # 0) Validaciones mínimas para tu flujo ECOERP (evita contratos “cojos”)
            missing = []
            if not getattr(so, 'property_id', False):
                missing.append("Propiedad")
            if not getattr(so, 'partner_id', False):
                missing.append("Inquilino")
            if not getattr(so, 'canon_property', False):
                missing.append("Canon de la propiedad")

            if missing:
                _logger.warning("No se auto-confirma por datos faltantes: %s ", missing)
                so.message_post(body=_("No se auto-confirma por datos faltantes: %s") % ", ".join(missing))
                continue

            # 1) Asegurar término de pago (si está vacío en el pedido)
            if not so.payment_term_id:
                # intenta el del partner y si no, inmediato
                partner_term = so.partner_invoice_id.property_payment_term_id or so.partner_id.property_payment_term_id
                so.payment_term_id = partner_term or term_immediate

            # 2) (Opcional) Si tu lógica exige plan, márcalo aquí o salta con nota
            # if not so.plan_id:
            #     so.message_post(body=_("Aviso: plan_id vacío. Se procede igualmente."))
            #     # o asigna uno por defecto si aplica: so.plan_id = self.env.ref('tu_modulo.tu_plan_defecto')

            try:
                so.with_context(mail_auto_subscribe_no_notify=True).action_confirm()
            except Exception as e:
                so.message_post(body=_("Auto-confirmación falló: %s") % e)

        # Marcar para revisión los casos con incremento en el pasado
        review_domain = [
            ('state', 'in', ('draft', 'sent')),
            ('x_rental_start_date', '!=', False),
            ('x_rental_start_date', '<=', today),
            ('date_increment', '!=', False),
            ('date_increment', '<', today),
        ]
        needs_review = self.search(review_domain, limit=limit)
        if needs_review:
            activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            for so in needs_review:
                if activity_type:
                    self.env['mail.activity'].create({
                        'res_id': so.id,
                        'res_model_id': self.env.ref('sale.model_sale_order').id,
                        'activity_type_id': activity_type.id,
                        'summary': _("Revisar contrato (incremento en el pasado)"),
                        'note': _("La orden quedó fuera del auto-confirm por tener date_increment < hoy."),
                        'user_id': so.user_id.id or self.env.user.id,
                        'date_deadline': today,
                    })
                else:
                    so.message_post(body=_("Revisar: incremento < hoy; no se auto-confirmó."))

        return True
    
    # cron de facturas de mandato, venta  y compra
    @api.model
    def _cron_generate_mandates_and_invoices(self, limit=500):
        """
        1) Selecciona contratos 'activos' a facturar.
        2) Deriva vinculados: inquilino (contrato) y propietarios (propiedad).
        3) Genera facturas de MANDATO (cliente = inquilino) por cada propietario según % participación.
        4) Genera facturas de VENTA (comisión de inmobiliaria al propietario), si existen líneas de comisión.
        5) Genera FACTURAS DE COMPRA (al propietario) por su participación.
        """
        _logger.info("=" * 80)
        _logger.info("INICIANDO CRON: _cron_generate_mandates_and_invoices (limit=%s)", limit)
        _logger.info("=" * 80)

        # Ejemplo: trae en lotes para evitar timeouts
        # 1) Trae órdenes confirmadas (= contratos)
        # domain = [('state', '=', 'sale')]
        domain = []
        contracts = self.search(domain, limit=limit)

        _logger.info("Contratos encontrados con state='sale': %s", len(contracts))

        if not contracts:
            _logger.info("No hay contratos para procesar. Finalizando cron.")
            return True

        # 2) Vincula contratos de esas órdenes
        total_orders = self.search_count(domain)
        remaining = max(0, total_orders - len(contracts))

        _logger.info("Total de contratos en sistema: %s, procesando: %s, restantes: %s",
                     total_orders, len(contracts), remaining)

        processed = 0
        for contract in contracts:
            _logger.info("-" * 80)
            _logger.info("PROCESANDO CONTRATO: %s (ID: %s)", contract.name, contract.id)
            _logger.info("  - Arrendatario: %s", contract.partner_id.name if contract.partner_id else 'NO DEFINIDO')
            _logger.info("  - Propiedad: %s", contract.x_account_analytic_account_id.name if contract.x_account_analytic_account_id else 'NO DEFINIDA')
            _logger.info("  - ecoerp_contract: %s", contract.ecoerp_contract)
            _logger.info("  - State: %s", contract.state)

            # TRANSACCIÓN ATÓMICA: Si falla algo, se revierte TODO
            _logger.info("  >> Iniciando transacción atómica (savepoint)...")
            with self.env.cr.savepoint():
                try:
                    # Generar facturas (mandato, comisión, compra)
                    _logger.info("  [1/2] Llamando a _generate_all_documents_for_period()...")
                    contract._generate_all_documents_for_period()
                    _logger.info("  [1/2] ✓ _generate_all_documents_for_period() completado")

                    # Generar asientos contables de servicios públicos
                    _logger.info("  [2/2] Llamando a _generate_utility_accounting_entries()...")
                    result = contract._generate_utility_accounting_entries()
                    if result:
                        _logger.info("  [2/2] ✓ _generate_utility_accounting_entries() completado. Asiento: %s", result.name)
                    else:
                        _logger.info("  [2/2] ⊘ _generate_utility_accounting_entries() no generó asiento (posiblemente saltado)")

                    processed += 1
                    _logger.info("  >> ✓ Transacción confirmada (commit)")
                    _logger.info("✓ CONTRATO %s PROCESADO EXITOSAMENTE (%s/%s)", contract.name, processed, len(contracts))

                    # Llamado seguro (no todas las builds exponen _notify_progress)
                    notify = getattr(self.env['ir.cron'], '_notify_progress', None)
                    if callable(notify):
                        notify(done=processed, remaining=remaining)

                except Exception as e:
                    _logger.error("  >> ✗ Error detectado. Ejecutando ROLLBACK de transacción...")
                    _logger.error(
                        "✗ ERROR procesando contrato %s: %s",
                        contract.name,
                        str(e),
                        exc_info=True
                    )
                    _logger.error("  >> Todas las facturas y asientos de este contrato fueron REVERTIDOS")
                    # El savepoint automáticamente hace rollback al salir del contexto con excepción
                    # Continuar con el siguiente contrato
                    continue

        _logger.info("=" * 80)
        _logger.info("CRON FINALIZADO: Procesados %s/%s contratos", processed, len(contracts))
        _logger.info("=" * 80)
        return True
    
    def _ecoerp_get_payment_option_id(self, fallback_names=('Mandato', 'Mandate')):
        """
        Devuelve un ID válido para l10n_co_edi_payment_option_id, si el campo existe.
        - Descubre el comodel del campo.
        - Intenta localizar una opción cuyo nombre contenga alguno de fallback_names.
        - Si no la encuentra, toma la primera disponible.
        Retorna un entero (o None si no hay campo/opciones).
        """
        Move = self.env['account.move']
        if 'l10n_co_edi_payment_option_id' not in Move._fields:
            return None

        field = Move._fields['l10n_co_edi_payment_option_id']
        option_model = field.comodel_name  # se autodetecta
        Option = self.env[option_model]

        # 1) Intentar por nombres típicos
        for label in fallback_names:
            opt = Option.search([('name', 'ilike', label)], limit=1)
            if opt:
                return opt.id

        # 2) Si no hay match por nombre, toma la primera opción existente
        opt = Option.search([], limit=1)
        return opt.id if opt else None


    def _ecoerp_apply_dian_fields_on_vals(self, vals, owner_partner=None):
        """
        Inserta en 'vals' solo los campos DIAN que existan:
        - l10n_co_edi_payment_option_id: usando _ecoerp_get_payment_option_id()
        - l10n_co_dian_mandate_principal:
            * si el campo es boolean -> True
            * si es many2one -> asigna owner_partner.id (si viene)
        """
        Move = self.env['account.move']

        # l10n_co_edi_payment_option_id
        if 'l10n_co_edi_payment_option_id' in Move._fields:
            payopt_id = self._ecoerp_get_payment_option_id()
            if payopt_id:
                vals['l10n_co_edi_payment_option_id'] = payopt_id

        # l10n_co_dian_mandate_principal
        if 'l10n_co_dian_mandate_principal' in Move._fields:
            f = Move._fields['l10n_co_dian_mandate_principal']
            if f.type == 'boolean':
                vals['l10n_co_dian_mandate_principal'] = True
            elif f.type == 'many2one':
                if owner_partner:
                    vals['l10n_co_dian_mandate_principal'] = owner_partner.id
            # Si fuera otro tipo, no lo tocamos

        return vals

    def _get_or_create_utility_journal(self):
        """
        Obtiene o crea el diario contable para cobro de servicios públicos.

        Returns:
            account.journal: Diario "COBRO DE OTROS CONCEPTOS" (tipo varios, código OTC)
        """
        _logger.info("         >> Buscando diario con code='OTC' y type='general'...")

        journal = self.env['account.journal'].search([
            ('code', '=', 'OTC'),
            ('type', '=', 'general')
        ], limit=1)

        if not journal:
            _logger.info("         >> Diario NO encontrado. Creando nuevo diario...")
            try:
                journal = self.env['account.journal'].create({
                    'name': 'COBRO DE OTROS CONCEPTOS',
                    'code': 'OTC',
                    'type': 'general',
                    'show_on_dashboard': True,
                })
                _logger.info("         >> ✓ Diario creado: %s (ID: %s)", journal.name, journal.id)
            except Exception as e:
                _logger.error("         >> ✗ ERROR al crear diario: %s", str(e), exc_info=True)
                raise
        else:
            _logger.info("         >> ✓ Diario encontrado: %s (ID: %s)", journal.name, journal.id)

        return journal

    def _build_transaction_cost_lines(self, amount, debit_account, credit_account, partner):
        """
        Construye líneas contables para costo de transacción.
        ESPECIAL: Mismo partner en débito y crédito (arrendatario).

        Args:
            amount (float): Monto del costo de transacción
            debit_account (account.account): Cuenta débito
            credit_account (account.account): Cuenta crédito
            partner (res.partner): Arrendatario (mismo para ambas líneas)

        Returns:
            list: Lista de diccionarios con valores de líneas contables
        """
        line_vals = []

        # Validar cuentas
        if not debit_account:
            raise UserError(
                _("No está configurada la cuenta débito para Costo Transacción. "
                  "Configure en Ajustes → ECOERP → Cuentas Contables.")
            )

        if not credit_account:
            raise UserError(
                _("No está configurada la cuenta crédito para Costo Transacción. "
                  "Configure en Ajustes → ECOERP → Cuentas Contables.")
            )

        # LÍNEA CRÉDITO: Arrendatario
        line_vals.append({
            'name': 'Costo Transacción - Arrendatario',
            'account_id': credit_account.id,
            'partner_id': partner.id,
            'credit': amount,
            'debit': 0.0,
            'sale_line_ids': [(6, 0, [self.id])],

        })

        # LÍNEA DÉBITO: Arrendatario (mismo partner)
        line_vals.append({
            'name': 'Costo Transacción - Arrendatario',
            'account_id': debit_account.id,
            'partner_id': partner.id,
            'debit': amount,
            'credit': 0.0,
            'sale_line_ids': [(6, 0, [self.id])],

        })

        return line_vals

    def _build_fixed_utility_lines(self, concept_name, amount, debit_account,
                                    credit_account, owner_lines, tenant_partner):
        """
        Construye líneas contables para conceptos de monto fijo (internet, TV, etc.)
        con prorrateo entre propietarios.

        Args:
            concept_name (str): Nombre del concepto
            amount (float): Monto total
            debit_account (account.account): Cuenta débito
            credit_account (account.account): Cuenta crédito
            owner_lines (recordset): Propietarios
            tenant_partner (res.partner): Arrendatario

        Returns:
            list: Lista de diccionarios con valores de líneas contables
        """
        line_vals = []

        # Validar cuentas
        if not debit_account:
            raise UserError(
                _("No está configurada la cuenta débito para %s. "
                  "Configure en Ajustes → ECOERP → Cuentas Contables.")
                % concept_name.replace('_', ' ').title()
            )

        if not credit_account:
            raise UserError(
                _("No está configurada la cuenta crédito para %s. "
                  "Configure en Ajustes → ECOERP → Cuentas Contables.")
                % concept_name.replace('_', ' ').title()
            )

        # LÍNEAS CRÉDITO: Por cada propietario (prorrateado)
        for owner_line in owner_lines:
            owner_amount = amount * (owner_line.participation_percent / 100.0)
            owner_amount = float_round(owner_amount, precision_digits=2)

            if float_is_zero(owner_amount, precision_digits=2):
                continue

            line_vals.append({
                'name': f"{concept_name.replace('_', ' ').title()} - {owner_line.owner_id.name} ({owner_line.participation_percent:.2f}%)",
                'account_id': credit_account.id,
                'partner_id': owner_line.owner_id.id,
                'credit': owner_amount,
                'debit': 0.0,
            })

        # LÍNEA DÉBITO: Arrendatario (100%)
        line_vals.append({
            'name': f"{concept_name.replace('_', ' ').title()} - Arrendatario",
            'account_id': debit_account.id,
            'partner_id': tenant_partner.id,
            'debit': amount,
            'credit': 0.0,
        })

        return line_vals

    def _build_utility_lines_from_meters(self, current_month, owner_lines, company, property_obj):
        """
        Construye líneas contables para servicios públicos basados en lecturas de medidor.

        Args:
            current_month (str): Período en formato YYYY-MM
            owner_lines (recordset): account.analytic.account.owner.line
            company (res.company): Compañía actual
            property_obj (account.analytic.account): Propiedad

        Returns:
            list: Lista de diccionarios con valores de líneas contables
        """
        line_vals = []

        # Mapeo de meter_type a configuración de cuentas
        meter_configs = {
            'water': {
                'name': 'Agua',
                'debit_account': company.utility_water_account_debit_id,
                'credit_account': company.utility_water_account_credit_id,
            },
            'energy': {
                'name': 'Energía',
                'debit_account': company.utility_energy_account_debit_id,
                'credit_account': company.utility_energy_account_credit_id,
            },
            'sanitation': {
                'name': 'Saneamiento',
                'debit_account': company.utility_sanitation_account_debit_id,
                'credit_account': company.utility_sanitation_account_credit_id,
            },
        }

        MeterReading = self.env['x.meter.reading']

        for meter_type, config in meter_configs.items():
            # Buscar lectura del mes actual
            reading = MeterReading.search([
                ('x_account_analytic_account_id', '=', property_obj.id),
                ('x_meter_id.meter_type', '=', meter_type),
                ('x_month', '=', current_month)
            ], limit=1)

            if not reading:
                raise UserError(
                    _("No se encontró lectura de %s para la propiedad '%s' en el período %s. "
                      "Registre la lectura antes de generar asientos.")
                    % (config['name'], property_obj.name, current_month)
                )

            # Validar existencia de cuentas
            if not config['debit_account']:
                raise UserError(
                    _("No está configurada la cuenta débito para %s. "
                      "Configure en Ajustes → ECOERP → Cuentas Contables.")
                    % config['name']
                )

            if not config['credit_account']:
                raise UserError(
                    _("No está configurada la cuenta crédito para %s. "
                      "Configure en Ajustes → ECOERP → Cuentas Contables.")
                    % config['name']
                )

            total_amount = reading.x_usage_cost

            if float_is_zero(total_amount, precision_digits=2):
                _logger.warning(
                    "Lectura de %s para propiedad %s tiene costo cero. Saltando...",
                    config['name'], property_obj.name
                )
                continue

            # LÍNEAS CRÉDITO: Por cada propietario (prorrateado)
            for owner_line in owner_lines:
                owner_amount = total_amount * (owner_line.participation_percent / 100.0)
                owner_amount = float_round(owner_amount, precision_digits=2)

                if float_is_zero(owner_amount, precision_digits=2):
                    continue

                line_vals.append({
                    'name': f"{config['name']} - {owner_line.owner_id.name} ({owner_line.participation_percent:.2f}%)",
                    'account_id': config['credit_account'].id,
                    'partner_id': owner_line.owner_id.id,
                    'credit': owner_amount,
                    'debit': 0.0,
                })

            # LÍNEA DÉBITO: Arrendatario (100%)
            line_vals.append({
                'name': f"{config['name']} - Arrendatario",
                'account_id': config['debit_account'].id,
                'partner_id': self.partner_id.id,
                'debit': total_amount,
                'credit': 0.0,
            })

        return line_vals

    def _generate_utility_accounting_entries(self):
        """
        Genera asiento contable automático para cobro de servicios públicos
        y otros conceptos asociados al contrato.

        Conceptos procesados:
        - Agua, Energía, Saneamiento (si servicios_publicos=True)
        - Internet (si internet=True)
        - TV Cable (si tv=True)
        - Administración Sostenimiento (si administracion_sostenimiento=True)
        - Costo Transacción (si costo_transaccion=True)

        Raises:
            UserError: Si faltan datos obligatorios o cuentas contables
        """
        self.ensure_one()
        _logger.info("    >> ENTRANDO a _generate_utility_accounting_entries() para contrato: %s", self.name)

        # 1. Validaciones iniciales
        _logger.info("    >> [PASO 1/9] Validaciones iniciales")
        _logger.info("       - ecoerp_contract: %s", self.ecoerp_contract)
        _logger.info("       - state: %s", self.state)

        # if not self.ecoerp_contract or self.state != 'sale':
        #     _logger.info("    >> SALIENDO: Contrato no es ECOERP o no está en state='sale'")
        #     return

        if not self.partner_id:
            _logger.error("    >> ERROR: Contrato sin arrendatario")
            raise UserError(_("El contrato %s no tiene arrendatario definido.") % self.name)

        if not self.x_account_analytic_account_id:
            _logger.error("    >> ERROR: Contrato sin propiedad")
            raise UserError(_("El contrato %s no tiene propiedad asociada.") % self.name)

        property_obj = self.x_account_analytic_account_id
        property_name = property_obj.name or 'Sin Nombre'
        company = self.company_id

        _logger.info("       ✓ Validaciones iniciales OK")

        # 2. Obtener mes actual
        _logger.info("    >> [PASO 2/9] Obtener mes actual")
        today = fields.Date.context_today(self)
        current_month = today.strftime("%Y-%m")
        current_year = today.year
        month_name_es = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        month_name = month_name_es.get(today.month, str(today.month))
        _logger.info("       - Fecha actual: %s", today)
        _logger.info("       - Mes a procesar: %s (%s %s)", current_month, month_name, current_year)

        # 3. Validar duplicados
        _logger.info("    >> [PASO 3/9] Validar duplicados")
        ref_pattern = f"COBRO OTROS CONCEPTOS - Propiedad {property_name} - {month_name} {current_year}"
        _logger.info("       - Referencia a buscar: '%s'", ref_pattern)

        existing_move = self.env['account.move'].search([
            ('ref', '=', ref_pattern),
            ('state', '!=', 'cancel')
        ], limit=1)

        if existing_move:
            _logger.info(
                "    >> SALIENDO: Asiento contable ya existe (ID: %s, Nombre: %s). Saltando...",
                existing_move.id, existing_move.name
            )
            return

        _logger.info("       ✓ No hay duplicados. Continuando...")

        # 4. Obtener propietarios (NO beneficiarios)
        _logger.info("    >> [PASO 4/9] Obtener propietarios")
        owner_lines = property_obj.owner_line_ids.filtered(lambda ol: not ol.is_main_payee)
        _logger.info("       - Propietarios encontrados: %s", len(owner_lines))

        if not owner_lines:
            _logger.error("    >> ERROR: Sin propietarios")
            raise UserError(
                _("La propiedad '%s' no tiene propietarios definidos. "
                  "Configure los propietarios antes de generar asientos.") % property_name
            )

        for owner_line in owner_lines:
            _logger.info("       - %s: %.2f%%", owner_line.owner_id.name, owner_line.participation_percent)

        # Validar suma de participaciones = 100%
        total_participation = sum(owner_lines.mapped('participation_percent'))
        _logger.info("       - Total participación: %.2f%%", total_participation)

        if not float_is_zero(total_participation - 100.0, precision_digits=2):
            _logger.error("    >> ERROR: Participación != 100%%")
            raise UserError(
                _("La suma de participaciones de propietarios en '%s' es %.2f%%. "
                  "Debe ser exactamente 100%%.") % (property_name, total_participation)
            )

        _logger.info("       ✓ Propietarios OK")

        # 5. Obtener diario contable
        _logger.info("    >> [PASO 5/9] Obtener diario contable")
        journal = self._get_or_create_utility_journal()
        _logger.info("       - Diario obtenido: %s (ID: %s, Código: %s)", journal.name, journal.id, journal.code)

        # 6. Construir líneas del asiento
        _logger.info("    >> [PASO 6/9] Construir líneas del asiento")
        line_vals = []

        # Verificar campos booleanos activos
        _logger.info("       - servicios_publicos: %s", self.servicios_publicos)
        _logger.info("       - internet: %s (monto: %.2f)", self.internet, self.monto_internet if self.internet else 0)
        _logger.info("       - tv: %s (monto: %.2f)", self.tv, self.monto_tv if self.tv else 0)
        _logger.info("       - administracion_sostenimiento: %s (monto: %.2f)",
                     self.administracion_sostenimiento,
                     self.monto_administracion_sostenimiento if self.administracion_sostenimiento else 0)
        _logger.info("       - costo_transaccion: %s (monto: %.2f)",
                     self.costo_transaccion,
                     self.costo_transaccion_monto if self.costo_transaccion else 0)

        # CONCEPTO 1-3: SERVICIOS PÚBLICOS (Agua, Energía, Saneamiento)
        if self.servicios_publicos:
            _logger.info("       [CONCEPTO 1-3] Procesando SERVICIOS PÚBLICOS...")
            try:
                utility_lines = self._build_utility_lines_from_meters(
                    current_month, owner_lines, company, property_obj
                )
                line_vals.extend(utility_lines)
                _logger.info("       [CONCEPTO 1-3] ✓ %s líneas agregadas", len(utility_lines))
            except Exception as e:
                _logger.error("       [CONCEPTO 1-3] ✗ ERROR: %s", str(e))
                raise

        # CONCEPTO 4: INTERNET
        if self.internet:
            _logger.info("       [CONCEPTO 4] Procesando INTERNET...")
            if float_is_zero(self.monto_internet, precision_digits=2):
                _logger.error("       [CONCEPTO 4] ✗ ERROR: Monto cero")
                raise UserError(
                    _("El contrato %s tiene habilitado 'Internet' pero el monto es cero. "
                      "Configure el monto de internet.") % self.name
                )

            try:
                internet_lines = self._build_fixed_utility_lines(
                    'internet',
                    self.monto_internet,
                    company.utility_internet_account_debit_id,
                    company.utility_internet_account_credit_id,
                    owner_lines,
                    self.partner_id
                )
                line_vals.extend(internet_lines)
                _logger.info("       [CONCEPTO 4] ✓ %s líneas agregadas", len(internet_lines))
            except Exception as e:
                _logger.error("       [CONCEPTO 4] ✗ ERROR: %s", str(e))
                raise

        # CONCEPTO 5: TV CABLE
        if self.tv:
            _logger.info("       [CONCEPTO 5] Procesando TV CABLE...")
            if float_is_zero(self.monto_tv, precision_digits=2):
                _logger.error("       [CONCEPTO 5] ✗ ERROR: Monto cero")
                raise UserError(
                    _("El contrato %s tiene habilitado 'TV' pero el monto es cero. "
                      "Configure el monto de TV.") % self.name
                )

            try:
                tv_lines = self._build_fixed_utility_lines(
                    'tv_cable',
                    self.monto_tv,
                    company.utility_tv_cable_account_debit_id,
                    company.utility_tv_cable_account_credit_id,
                    owner_lines,
                    self.partner_id
                )
                line_vals.extend(tv_lines)
                _logger.info("       [CONCEPTO 5] ✓ %s líneas agregadas", len(tv_lines))
            except Exception as e:
                _logger.error("       [CONCEPTO 5] ✗ ERROR: %s", str(e))
                raise

        # CONCEPTO 6: ADMINISTRACIÓN SOSTENIMIENTO
        if self.administracion_sostenimiento:
            _logger.info("       [CONCEPTO 6] Procesando ADMINISTRACIÓN SOSTENIMIENTO...")
            if float_is_zero(self.monto_administracion_sostenimiento, precision_digits=2):
                _logger.error("       [CONCEPTO 6] ✗ ERROR: Monto cero")
                raise UserError(
                    _("El contrato %s tiene habilitado 'Administración Sostenimiento' "
                      "pero el monto es cero. Configure el monto.") % self.name
                )

            try:
                admin_lines = self._build_fixed_utility_lines(
                    'admin_sostenimiento',
                    self.monto_administracion_sostenimiento,
                    company.utility_admin_sostenimiento_account_debit_id,
                    company.utility_admin_sostenimiento_account_credit_id,
                    owner_lines,
                    self.partner_id
                )
                line_vals.extend(admin_lines)
                _logger.info("       [CONCEPTO 6] ✓ %s líneas agregadas", len(admin_lines))
            except Exception as e:
                _logger.error("       [CONCEPTO 6] ✗ ERROR: %s", str(e))
                raise

        # CONCEPTO 7: COSTO TRANSACCIÓN (especial: mismo partner débito/crédito)
        if self.costo_transaccion:
            _logger.info("       [CONCEPTO 7] Procesando COSTO TRANSACCIÓN...")
            if float_is_zero(self.costo_transaccion_monto, precision_digits=2):
                _logger.error("       [CONCEPTO 7] ✗ ERROR: Monto cero")
                raise UserError(
                    _("El contrato %s tiene habilitado 'Costo Transacción' "
                      "pero el monto es cero. Configure el monto.") % self.name
                )

            try:
                trans_lines = self._build_transaction_cost_lines(
                    self.costo_transaccion_monto,
                    company.utility_transaction_cost_account_debit_id,
                    company.utility_transaction_cost_account_credit_id,
                    self.partner_id
                )
                line_vals.extend(trans_lines)
                _logger.info("       [CONCEPTO 7] ✓ %s líneas agregadas", len(trans_lines))
            except Exception as e:
                _logger.error("       [CONCEPTO 7] ✗ ERROR: %s", str(e))
                raise

        # 7. Validar que hay líneas para crear
        _logger.info("    >> [PASO 7/9] Validar líneas construidas")
        _logger.info("       - Total líneas construidas: %s", len(line_vals))

        if not line_vals:
            _logger.info(
                "    >> SALIENDO: No hay conceptos habilitados para el contrato %s. No se genera asiento.",
                self.name
            )
            return

        # 8. Crear asiento contable
        _logger.info("    >> [PASO 8/9] Crear asiento contable")
        _logger.info("       - Diario: %s", journal.name)
        _logger.info("       - Fecha: %s", today)
        _logger.info("       - Referencia: %s", ref_pattern)
        _logger.info("       - Líneas: %s", len(line_vals))

        move_vals = {
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': today,
            'ref': ref_pattern,
            'line_ids': [(0, 0, line) for line in line_vals],
        }

        try:
            move = self.env['account.move'].create(move_vals)
            _logger.info("       ✓ Asiento creado: %s (ID: %s)", move.name, move.id)
        except Exception as e:
            _logger.error("       ✗ ERROR al crear asiento: %s", str(e), exc_info=True)
            raise

        # 9. Publicar asiento
        _logger.info("    >> [PASO 9/9] Publicar asiento")
        try:
            move.action_post()
            _logger.info("       ✓ Asiento publicado exitosamente")
        except Exception as e:
            _logger.error("       ✗ ERROR al publicar asiento: %s", str(e), exc_info=True)
            raise

        _logger.info(
            "    >> ✓✓✓ ASIENTO CONTABLE %s CREADO Y PUBLICADO EXITOSAMENTE ✓✓✓",
            move.name
        )
        _logger.info("       Contrato: %s, Propiedad: %s, Período: %s-%s",
                     self.name, property_name, month_name, current_year)

        return move

    def _generate_all_documents_for_period(self):
        self.ensure_one()
        tenant = self.partner_id
        if not tenant:
            raise UserError(_("El contrato %s no tiene inquilino definido.") % self.display_name)

        if not self.property_id:
            raise UserError(_("El contrato %s no tiene propiedad asociada.") % self.display_name)
        
        if not self.canon_property>0:
            raise UserError(_("El contrato %s no tiene canon correctamente definido.") % self.display_name)

        # 2) Propietarios vinculados y participaciones
        owners = self.property_id._get_property_owners_with_shares()  # implementa en propiedad
        if not owners:
            raise UserError(_("La propiedad %s no tiene propietarios con % de participación.") % self.property_id.display_name)

        # 3) Líneas de cobro (o default por canon + producto Tarifa de alquiler)
        charge_lines = self._get_contract_charges() or []
        if not charge_lines:
            charge_lines = self._default_rent_charge_line() or []

        # Agregar (concatenar) la línea de Administración PH si aplica
        admin_lines = self._default_admin_charge_line()
        if admin_lines:
            charge_lines += admin_lines

        if not charge_lines:
            raise UserError(_("No hay tarifa de alquiler."))
        
        # confirmamos la orden asociada al contrato
        if self.state in ('draft', 'sent'):
            self.action_confirm()
        # 3.a) Mandato: por cada propietario vamos a cargrar su porcentaje que le corresponde del canon de la propiedad y crea factura al inquilino
        mandate_moves = []
        for owner, share in owners:  # owner: res.partner, share: 0..1
            # Validar si se debe aplicar IVA según normatividad tributaria colombiana:
            # - Propietario responsable de IVA: l10n_co_edi_fiscal_regimen in ('48', 'ZA')
            # - Contrato comercial: x_uso_destino_rel == 'commercial'
            # Si ambas condiciones se cumplen, el IVA debe aplicarse
            owner_is_vat_responsible = owner.l10n_co_edi_fiscal_regimen in ('48', 'ZA')
            contract_is_commercial = self.x_uso_destino_rel == 'commercial'

            # Solo excluir impuestos si el contrato es residencial O si el propietario NO es responsable de IVA
            exclude_taxes = not (owner_is_vat_responsible and contract_is_commercial)

            lines = self._build_mandate_invoice_lines(charge_lines, share, exclude_taxes=exclude_taxes)
            move = self._create_customer_invoice_mandate(tenant, owner, lines)
            mandate_moves.append(move)
            _logger.info("Owner: %s | VAT Responsible: %s | Commercial: %s | Exclude Taxes: %s | MOVE: %s",
                        owner.name, owner_is_vat_responsible, contract_is_commercial, exclude_taxes, move)

        # 4) Comisión inmobiliaria (venta)
        commission_lines = self._get_commission_lines_for_owner_period()
        if commission_lines:
            for owner_id, amounts in commission_lines.items():
                owner = self.env['res.partner'].browse(owner_id)
                self._create_sale_invoice_commission(owner, amounts)
                _logger.info("LINES: %s COMISION %s", lines, amounts)                

        # 5) Compra al propietario por su participación
        for owner, share in owners:            
            bill_lines = self._build_vendor_bill_lines(self.canon_property, share)
            self._create_vendor_bill_to_owner(owner, bill_lines)
            _logger.info("bill_lines: %s owner %s", bill_lines, owner)

        return True

    # ------------ Helpers específicos ECOERP ------------

    def _get_contract_charges(self):
        """Devuelve las líneas de cobro propias del contrato (si existen)."""
        return []

    def _default_rent_charge_line(self):
        """Si no hay líneas, usa canon_property con el producto 'Tarifa de alquiler'."""
        canon = self.canon_property
        try:
            # Usar producto para facturas de VENTA (out_invoice)
            product = self._get_product_tarifa_alquiler(invoice_type='out_invoice')
            return [{'product_id': product.id, 'amount': canon}]
        except Exception as e:
            _logger.exception("ECOERP DEBUG: fallo resolviendo producto Tarifa de alquiler")
            # Si quieres abortar aquí:
            # raise
            # O registrar y continuar:
            return []
        
    def _default_admin_charge_line(self):
        """Línea de cargo por Administración PH (VENTA) si aplica."""
        self.ensure_one()
        if not getattr(self, 'cobro_comision_admin_ph', False):
            return []
        administracion_ph = float(getattr(self, 'administracion_ph', 0.0) or 0.0)
        monto_admin_pct   = float(getattr(self, 'monto_comision_admin_ph', 0.0) or 0.0)
        if administracion_ph <= 0.0 or monto_admin_pct <= 0.0:
            return []
        product = self._get_product_administracion_ph(invoice_type='out_invoice')
        # value = (administracion_ph * monto_admin_pct) / 100.0
        value = monto_admin_pct
        return [{
            'product_id': product.id,
            'amount': value,
            'name': 'Administración PH',
        }]

    def _get_tax_iva_19_sale(self):
        """
        Obtiene el impuesto IVA 19% para ventas.

        Estrategia de búsqueda:
        1. Por XML ID: l10n_co.l10n_co_tax_8
        2. Por nombre: "19% IVA" (traducción en español)
        3. Por nombre alternativo: "19%" + type_tax_use='sale' + amount=19.0

        Returns:
            account.tax: Impuesto IVA 19% para ventas, o None si no se encuentra
        """
        Tax = self.env['account.tax'].sudo()
        company_id = self.company_id.id or self.env.company.id

        # Estrategia 1: Intentar por XML ID
        try:
            tax = self.env.ref('l10n_co.l10n_co_tax_8', raise_if_not_found=False)
            if tax and tax.type_tax_use == 'sale' and tax.amount == 19.0:
                _logger.info("✓ Impuesto IVA 19%% encontrado por XML ID: %s", tax.name)
                return tax
        except Exception as e:
            _logger.debug("No se encontró por XML ID l10n_co.l10n_co_tax_8: %s", e)

        # Estrategia 2: Buscar por nombre "19% IVA" (español)
        tax = Tax.search([
            ('name', 'ilike', '19% IVA'),
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', 19.0),
            ('company_id', '=', company_id),
            ('active', '=', True),
        ], limit=1)

        if tax:
            _logger.info("✓ Impuesto IVA 19%% encontrado por nombre '19%% IVA': %s (ID: %s)", tax.name, tax.id)
            return tax

        # Estrategia 3: Buscar por nombre "19%" + criterios
        tax = Tax.search([
            ('name', 'ilike', '19%'),
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', 19.0),
            ('company_id', '=', company_id),
            ('active', '=', True),
        ], limit=1)

        if tax:
            _logger.info("✓ Impuesto IVA 19%% encontrado por criterios: %s (ID: %s)", tax.name, tax.id)
            return tax

        # No se encontró el impuesto
        _logger.error("✗ No se encontró el impuesto IVA 19%% para ventas (company_id=%s)", company_id)
        _logger.error("  → Verifique que existe un impuesto con: type_tax_use='sale', amount=19.0, name='19%% IVA'")
        return None

    def _build_mandate_invoice_lines(self, charge_lines, share, exclude_taxes):
        """
        Genera líneas para factura de mandato: prorratea por participación y maneja impuestos según normatividad.

        Args:
            charge_lines: Lista de diccionarios con 'product_id', 'amount', 'name'
            share: Participación del propietario (0.0 a 1.0)
            exclude_taxes: Si True, mantiene el impuesto del producto (0% IVA Exc); si False, aplica IVA 19%

        Lógica de impuestos según normatividad tributaria colombiana:
            - exclude_taxes=True: Mantiene el impuesto del producto (0% IVA Exc)
              → Para la DIAN es obligatorio tener un impuesto registrado, incluso si es 0% Excluido
              → Contratos residenciales o propietarios no responsables de IVA

            - exclude_taxes=False: Reemplaza por IVA 19%
              → Contratos comerciales + propietarios responsables de IVA (régimen '48' o 'ZA')
              → Se reemplaza el impuesto del producto (0% IVA Exc) por el impuesto IVA 19%
        """
        cmds = []

        # Obtener el impuesto IVA 19% para ventas
        tax_iva_19 = None
        if not exclude_taxes:
            tax_iva_19 = self._get_tax_iva_19_sale()

        for ch in charge_lines:
            price = (ch['amount'] or 0.0) * (share or 0.0)
            line_vals = {
                'product_id': ch['product_id'],
                'quantity': 1.0,
                'price_unit': price,
                'name': ch.get('name') or _('Canon de arrendamiento'),
                'sale_line_ids': [(6, 0, [self.id])],
            }

            if exclude_taxes:
                # Caso 1: Contrato residencial O propietario no responsable de IVA
                # → NO hacer nada, dejar que Odoo aplique el impuesto del producto (0% IVA Exc)
                # → Para la DIAN es obligatorio tener un impuesto registrado
                pass
            else:
                # Caso 2: Contrato comercial + propietario responsable de IVA
                # → Reemplazar el impuesto del producto (0% IVA Exc) por IVA 19%
                if tax_iva_19:
                    line_vals['tax_ids'] = [(6, 0, [tax_iva_19.id])]
                else:
                    _logger.error("✗ No se pudo aplicar IVA 19%% en factura de mandato")
                    # Fallback: dejar los impuestos del producto (0% IVA Exc)
                    pass

            cmds.append((0, 0, line_vals))
        return cmds

    def _create_customer_invoice_mandate(self, tenant, owner, invoice_line_cmds):
            """
            Factura de cliente (mandato), partner=inquilino, relaciona propietario e info de mandato.

            FLUJO DE IMPUESTOS:
            1. _build_mandate_invoice_lines() asigna IVA 19% manualmente (si aplica)
            2. Este método aplica la posición fiscal del inquilino sobre el IVA 19%
            3. Resultado: IVA 19% + Retención en la Fuente (según posición fiscal)

            CONFIGURACIÓN DE POSICIÓN FISCAL (IMPORTANTE):
            Para que la retención se aplique correctamente junto con el IVA, debes crear un
            GRUPO DE IMPUESTOS (Tax Group) en Odoo que incluya ambos:

            Opción 1 - Usando Tax Group (RECOMENDADO):
            - Ir a Contabilidad > Configuración > Impuestos
            - Crear nuevo impuesto tipo "Grupo de Impuestos"
            - Nombre: "IVA 19% + RteFte 3.5%"
            - Hijos: [IVA 19%, Retención 3.5%]
            - Luego en Posición Fiscal:
              IVA 19% → IVA 19% + RteFte 3.5% (el grupo)

            Opción 2 - Dejando que Odoo lo calcule automáticamente:
            - No asignar tax_ids manualmente en _build_mandate_invoice_lines()
            - Dejar que el producto tenga su impuesto por defecto
            - La posición fiscal aplicará la retención automáticamente
            """
            if not isinstance(invoice_line_cmds, list):
                raise UserError(f"invoice_line_ids debe ser lista de comandos O2M; llegó: {type(invoice_line_cmds).__name__} = {invoice_line_cmds!r}")

            if not invoice_line_cmds:
                self.message_post(body=_("ECOERP: mandato omitido (monto 0) para %s.") % tenant.display_name)
                return self.env['account.move']

            immediate_term = self.env.ref('account.account_payment_term_immediate')  # término de pago inmediato
            vals = {
                'move_type': 'out_invoice',               # factura cliente
                'partner_id': tenant.id,
                'invoice_line_ids': invoice_line_cmds,    # comandos O2M
                'invoice_payment_term_id': immediate_term.id if immediate_term else False,
                'currency_id': self.currency_id.id,
                'company_id': self.company_id.id,
                'invoice_origin': self.display_name,
                # Campos DIAN:
                'l10n_co_edi_operation_type': '11',
                'l10n_co_dian_mandate_principal': owner.id,
                # 'x_contract_id': self.id,
                # 'x_property_id': self.property_id.id,
            }

            # ⚠️ CRÍTICO: Asignar posición fiscal del inquilino explícitamente
            # Odoo normalmente lo hace automáticamente, pero cuando se asignan tax_ids manualmente
            # en las líneas, el campo fiscal_position_id puede no calcularse correctamente.
            # Por eso lo asignamos explícitamente aquí.
            if tenant.property_account_position_id:
                vals['fiscal_position_id'] = tenant.property_account_position_id.id

            # vals = self._ecoerp_apply_dian_fields_on_vals(vals, owner_partner=owner)
            move = self.env['account.move'].create(vals)

            # ⚠️ IMPORTANTE: Asegurar que las líneas de factura estén disponibles
            # Cuando se crean líneas con comandos (0, 0, {...}), necesitamos
            # invalidar el cache para poder leerlas inmediatamente después
            move.invalidate_recordset(['invoice_line_ids'])

            # ========================================================================
            # APLICAR POSICIÓN FISCAL DEL INQUILINO (TENANT)
            # ========================================================================
            # PROBLEMA: Cuando asignamos tax_ids manualmente en _build_mandate_invoice_lines(),
            # Odoo NO aplica automáticamente la posición fiscal porque los impuestos
            # ya están definidos y no se ejecuta _compute_tax_ids().
            #
            # SOLUCIÓN: Forzar la aplicación de la posición fiscal usando el método
            # _get_computed_taxes() de Odoo, que internamente ejecuta:
            #   fiscal_position_id.map_tax(tax_ids)
            #
            # FLUJO:
            # 1. _build_mandate_invoice_lines() asignó: IVA 19% (manualmente)
            # 2. _get_computed_taxes() toma ese IVA 19% y aplica posición fiscal
            # 3. Resultado: IVA 19% + Retención (según mapeo de posición fiscal)
            # ========================================================================

            if move.fiscal_position_id:
                fiscal_position = move.fiscal_position_id

                # Mostrar mapeo de impuestos de la posición fiscal
                if hasattr(fiscal_position, 'tax_ids'):
                    if fiscal_position.tax_ids:
                        # Detectar reglas conflictivas (mismo impuesto origen mapeado a múltiples destinos)
                        source_taxes = {}
                        for tax_map in fiscal_position.tax_ids:
                            src_id = tax_map.tax_src_id.id if tax_map.tax_src_id else None
                            if src_id:
                                if src_id not in source_taxes:
                                    source_taxes[src_id] = []
                                source_taxes[src_id].append(tax_map)

                # Filtrar líneas: incluir líneas de producto, excluir líneas de texto (section/note)
                # En Odoo 18, las líneas normales tienen display_type='product' o False
                # Las líneas de texto tienen display_type='line_section' o 'line_note'
                lines_to_process = move.invoice_line_ids.filtered(
                    lambda l: l.display_type not in ('line_section', 'line_note')
                )

                # Recalcular impuestos en cada línea de factura usando el método nativo de Odoo
                for idx, line in enumerate(lines_to_process, 1):

                    # Guardar impuestos originales para logging
                    original_taxes = line.tax_ids
                    if original_taxes:
                        for tax in original_taxes:
                            _logger.info("    -> %s (ID: %s, amount: %s%%)", tax.name, tax.id, tax.amount)
                    else:
                        _logger.info("    Sin impuestos")

                    # Usar el método nativo _get_computed_taxes()
                    _logger.info("  - Llamando a _get_computed_taxes()...")
                    try:
                        computed_taxes = fiscal_position.map_tax(original_taxes)
                        # computed_taxes = line._get_computed_taxes()
                        
                    except Exception as e:
                        _logger.error("  ERROR al llamar _get_computed_taxes(): %s", e, exc_info=True)
                        computed_taxes = original_taxes

                    if computed_taxes != original_taxes:
                        # Aplicar los impuestos mapeados (con retención)
                        line.tax_ids = computed_taxes

            # Publica si corresponde a tu política:
            # move.action_post()
            return move.action_post()
    
    def _get_or_create_commission_product(self):
        """Obtiene el producto de comisión configurado en la compañía.
        Si no está configurado:
          1) Busca 'tasa por honorarios' (ilike) en productos.
          2) Si no existe, lo crea (Servicio).
        En ambos casos, lo asigna a company_id.ecoerp_product_owner_payment_id y lo devuelve.
        """
        self.ensure_one()
        company = self.company_id

        # 1) Si ya está configurado en la compañía, úsalo
        product = getattr(company, 'ecoerp_product_owner_payment_id', False)
        if product:
            return product

        Product = self.env['product.product'].sudo()

        # 2) Buscar existente por nombre (ilike)
        # product = Product.search([('name', 'ilike', 'tasa por honorarios')], limit=1)
        product = self.env.ref('industry_real_estate.product_product_44', raise_if_not_found=False)
        if not product:
            # 3) Crear como Servicio (detailed_type='service')
            product = Product.create({
                'name': 'Comisión inmobiliaria',
                'detailed_type': 'service',
                'sale_ok': True,
                'purchase_ok': False,
                # Opcionales según tu flujo:
                # 'lst_price': 0.0,  # precio unitario por defecto
                # 'taxes_id': [(6, 0, [])],  # deja que la categoría/compañía defina impuestos
            })

        # 4) Asignar a la compañía (guardamos configuración)
        company.sudo().write({'ecoerp_product_owner_payment_id': product.id})
        return product

    def _get_commission_lines_for_owner_period(self):
        """Devuelve {owner: [comandos de creación de líneas]} si hay comisiones que facturar (venta)."""
        self.ensure_one()
        result = {}

        # 1) Origen del % administración: toma valor propio si está definido; si no, el de la compañía
        company_pct = float(getattr(self.company_id, 'porcentaje_comision_inmobiliaria', 0.0) or 0.0)
        own_pct = float(getattr(self, 'comision_inmobiliaria_porcentaje', 0.0) or 0.0)
        admin_pct = own_pct if own_pct > 0.0 else company_pct

        # 2) Producto de comisión (debe existir)
        product = self._get_or_create_commission_product()
        if not product:
            _logger.error("No existe producto de comisión para el contrato %s", self.name or '')
            return result  # o raise UserError si debe ser obligatorio

        # 3) Base del canon (monto del inquilino)
        tenant_amount = float(self.canon_property or 0.0)

        # 4) Comisión base (porcentaje sobre canon)
        commission_base = (tenant_amount * admin_pct) / 100.0

        # 5) Cobro administración PH (base inmutable)
        cobro_admin_base = 0.0
        if getattr(self, 'cobro_comision_admin_ph', False) \
        and float(getattr(self, 'administracion_ph', 0.0) or 0.0) > 0.0 \
        and float(getattr(self, 'monto_comision_admin_ph', 0.0) or 0.0) > 0.0:
            cobro_admin_base = (float(self.administracion_ph) * float(self.monto_comision_admin_ph)) / 100.0

        # 6) Moneda para redondeo
        currency = getattr(self, 'currency_id', False) or self.company_id.currency_id

        # 7) Itera dueños no beneficiarios
        for ol in self.property_id.non_beneficiary_line_ids:
            owner = ol.owner_id
            com_per = ol.comision_personalizada or 0.0
            if not owner:
                _logger.warning("Línea sin owner en contrato %s (linea id %s)", self.name or '', ol.id)
                continue
            if com_per>0.0:
                commission_base = (tenant_amount * com_per) / 100.0 # comisión por trato especial

            pct = float(ol.participation_percent or 0.0)
            owner_share = pct / 100.0

            # Monto del dueño: su % de la comisión base + su % del cobro admin base
            amount = (commission_base * owner_share) + (cobro_admin_base * owner_share)

            # Redondeo monetario si hay currency
            amount = currency.round(amount) if currency else round(amount, 2)

            if amount <= 0.0:
                _logger.info("Monto de comisión 0 para owner %s en contrato %s (pct=%s)", owner.display_name, self.name or '', pct)
                continue

            lines_vals = {
                'owner_id': owner.id,
                'product_id': product.id,
                'property_id': self.property_id.id,
                'description': _('Comisión por contrato %s') % (self.name or ''),
                'amount': amount,
                'quantity': 1.0,
                'price_unit': amount,
                'porcent': ol.participation_percent or 0.0,
                'date': fields.Date.today(),
                'invoice_date': fields.Date.context_today(self),
                'sale_line_ids': [(6, 0, [self.id])],
            }
            cmds = [(0, 0, lines_vals)]
            result.setdefault(owner, []).extend(cmds)

        return result
            

    def _create_sale_invoice_commission(self, owner, line_commands):
        """owner: res.partner; amounts: iterable de montos a facturar (floats)."""
        self.ensure_one()
        company = self.company_id
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'), ('company_id', '=', company.id)
        ], limit=1)
        if not journal:
            raise UserError("No hay diario de ventas configurado para la compañía.")

        product = self._get_or_create_commission_product()
        owner_id = owner.id if hasattr(owner, 'id') else int(owner)

        # Campos válidos comunes en account.move.line (ventas)
        ALLOWED = {
            'name', 'product_id', 'quantity', 'price_unit', 'discount',
            'tax_ids', 'analytic_account_id', 'analytic_distribution',
            'analytic_tag_ids', 'account_id', 'display_type',
            'exclude_from_invoice_tab',
        }

        norm_cmds = []
        for item in (line_commands or []):
            # Acepta (0,0,{...}) o dict
            vals = {}
            if isinstance(item, tuple) and len(item) == 3 and item[0] == 0 and isinstance(item[2], dict):
                vals = dict(item[2])   # copia
            elif isinstance(item, dict):
                vals = dict(item)
            else:
                # Si te llegan montos (floats), conviértelos a dicts:
                try:
                    amount = float(item or 0.0)
                    if not amount:
                        continue
                    vals = {
                        'product_id': product.id,
                        'name': f'Comisión por contrato {self.name or ""}',
                        'quantity': 1.0,
                        'price_unit': amount,
                    }
                except Exception:
                    raise UserError("Formato de línea/comisión inválido: %s" % (item,))

            # Completa valores básicos
            vals.setdefault('product_id', product.id)
            vals.setdefault('name', f'Comisión por contrato {self.name or ""}')
            vals.setdefault('quantity', 1.0)
            vals.setdefault('sale_line_ids', [(6, 0, [self.id])])

            # LIMPIA claves no soportadas (como owner_id, property_id, etc.)
            vals = {k: v for k, v in vals.items() if k in ALLOWED}

            # Si vas a marcar la propiedad, usa analítica:
            # vals.setdefault('analytic_account_id', self.property_id.analytic_account_id.id)

            norm_cmds.append((0, 0, vals))

        if not norm_cmds:
            return False

        vals_move = {
            'move_type': 'out_invoice',
            'partner_id': owner_id.id,             # el propietario va aquí
            'company_id': company.id,
            'journal_id': journal.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_line_ids': norm_cmds,
            'l10n_co_edi_operation_type':'10',
            'currency_id': self.currency_id.id,
            'invoice_origin': self.display_name,
            'date': fields.Date.today(),
            # 'x_contract_id': self.id,
            # 'x_property_id': self.property_id.id,
        }
        _logger.info("CREATING COMMISSION MOVE VALS: %s", vals_move)
        return self.env['account.move'].create(vals_move).action_post()

    def _build_vendor_bill_lines(self, canon, share, precision=2):
        """Líneas de compra al propietario por su % del canon."""
        try:
            amount = (canon or 0.0) * (share or 0.0)
            if amount < 0.0:
                amount = abs(amount)
            if float_is_zero(amount, precision_digits=precision):
                # si por redondeo quedó 0, no crear línea
                return []
            # Usar producto para facturas de COMPRA (in_invoice)
            product = self._get_product_tarifa_alquiler(invoice_type='in_invoice')
            product2 = self._get_product_administracion_ph(invoice_type='in_invoice')
            if not product:
                raise UserError(_("No se encontró el producto de Participación del canon para compras (in_invoice)."))

            cobro_admin = 0.0
            if getattr(self, 'cobro_comision_admin_ph', False) and (getattr(self, 'administracion_ph', 0.0) or 0.0) > 0.0 and (getattr(self, 'monto_comision_admin_ph', 0.0) or 0.0) > 0.0:
                # Ejemplo: administracion_ph * monto_comision_admin_ph / 100 (ajusta si tu lógica real es distinta)
                # cobro_admin = (self.administracion_ph * self.monto_comision_admin_ph) / 100.0
                cobro_admin = self.monto_comision_admin_ph * (share or 0.0)
                
            # Evitar que la segunda línea haga negativo el neto
            if cobro_admin > amount:
                cobro_admin = amount
            
             # 4) Armar líneas
            commands = []

            # (a) Línea de participación del canon (neta si hay admin)
            price_unit_main = amount - (cobro_admin if cobro_admin and product2 else 0.0)
            if float_is_zero(price_unit_main, precision_digits=precision) is False:
                commands.append((0, 0, {
                    'product_id': product.id,
                    'quantity': 1.0,
                    'price_unit': price_unit_main,
                    'name': _('Participación del canon'),
                    # Usa esta relación solo si el método corre en sale.order.line:
                    # 'sale_line_ids': [(6, 0, [self.id])],
                    # Impuestos: deja que el producto/proveedor defina; o setea tax_ids aquí si corresponde.
                }))

            # (b) Línea de administración (opcional)
            if cobro_admin and product2:
                if float_is_zero(cobro_admin, precision_digits=precision) is False:
                    commands.append((0, 0, {
                        'product_id': product2.id,
                        'quantity': 1.0,
                        'price_unit': cobro_admin,
                        'name': _('Participación de administración'),
                        # 'sale_line_ids': [(6, 0, [self.id])],
                    }))

            return commands
            
        except Exception as e:
            _logger.exception("ECOERP DEBUG: fallo resolviendo producto Tarifa de alquiler")
            # Si quieres abortar aquí:
            # raise
            # O registrar y continuar:
            return True

    def _create_vendor_bill_to_owner(self, owner, bill_line_cmds):
        """Factura de compra al propietario por su participación."""
        # Guardia: validar tipo
        if not isinstance(bill_line_cmds, list):
            raise UserError(f"invoice_line_ids debe ser lista de comandos O2M; llegó: {type(bill_line_cmds).__name__} = {bill_line_cmds!r}")

        if not bill_line_cmds:
            self.message_post(body=_("ECOERP: compra a %s omitida (monto 0).") % owner.display_name)
            return self.env['account.move']  # vacío, pero no booleano
        vals = {
            'move_type': 'in_invoice',
            'partner_id': owner.id,
            'invoice_line_ids': bill_line_cmds,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'invoice_origin': self.display_name,
            'l10n_co_edi_operation_type': '10',
            'date': fields.Date.today(),
            'invoice_date': fields.Date.context_today(self),
            # 'x_contract_id': self.id,
            # 'x_property_id': self.property_id.id,
        }

        _logger.info("Creando factura de proveedor (in_invoice) a propietario %s", owner.name)

        bill = self.env['account.move'].create(vals)

        _logger.info("  ✓ Factura creada con operation_type: %s", bill.l10n_co_edi_operation_type)

        return bill.action_post()
    
    def _get_product_administracion_ph(self, invoice_type='out_invoice'):
        """
        Devuelve product.product (variante) para 'Administración de propiedad'.

        - Intenta por XMLID (template -> variant si aplica).
        - Fallback por código/nombre.
        - Tolerante a multi-compañía.
        """
        Product  = self.env['product.product']
        Template = self.env['product.template']

        # 1) Determinar XMLID y códigos según tipo de factura
        if invoice_type == 'in_invoice':
            xmlid = 'industry_real_estate.product_product_52'  # Producto para COMPRAS
            fallback_codes = ['ADMIN_PH_COMPRA', 'ADMIN_PH']
            _logger.debug("Buscando producto para COMPRA (in_invoice): XMLID=%s", xmlid)
        else:  # out_invoice (default)
            xmlid = 'industry_real_estate.product_product_51'  # Producto para VENTAS
            fallback_codes = ['ADMIN_PH_VENTA', 'ADMIN_PH']
            _logger.debug("Buscando producto para VENTA (out_invoice): XMLID=%s", xmlid)

        # 2) Por XMLID
        prod = self.env.ref(xmlid, raise_if_not_found=False)

        if prod:
            if prod._name == 'product.template':
                prod = prod.product_variant_id
            if prod and prod.exists():
                # Multi-compañía: preferir producto sin compañía o de la misma
                if prod.company_id and self.env.company and prod.company_id != self.env.company:
                    prod2 = Product.search([
                        ('id', '=', prod.id),
                        '|', ('company_id', '=', False),
                            ('company_id', '=', self.env.company.id)
                    ], limit=1)
                    if prod2:
                        prod = prod2
                _logger.debug("  ✓ Producto encontrado por XMLID: %s (ID: %s)", prod.name, prod.id)
                return prod

        # 3) Fallback por código/nombre
        _logger.debug("  >> XMLID no encontrado, intentando fallback por código...")

        # Construir dominio con múltiples códigos posibles
        domain = []
        for i, code in enumerate(fallback_codes):
            if i > 0:
                domain.insert(0, '|')
            domain.append(('default_code', '=', code))

        # Agregar búsqueda por nombre
        domain.insert(0, '|')
        domain.insert(0, '|')
        domain.extend([
            ('name', 'ilike', 'Property management'),
            ('name', 'ilike', 'Administración ph')
        ])

        if self.env.company:
            domain += ['|', ('company_id', '=', False),
                            ('company_id', '=', self.env.company.id)]

        prod = Product.search(domain, limit=1)
        if prod:
            _logger.debug("  ✓ Producto encontrado por código/nombre: %s (ID: %s)", prod.name, prod.id)
            return prod

        tmpl = Template.search(domain, limit=1)
        if tmpl:
            prod = tmpl.product_variant_id
            if prod and prod.exists():
                _logger.debug("  ✓ Producto encontrado por template: %s (ID: %s)", prod.name, prod.id)
                return prod

        # 4) No se encontró
        _logger.error("  ✗ No se encontró producto 'Tarifa de alquiler' para %s", invoice_type)
        raise UserError(
            f"No se encontró el producto 'Tarifa de alquiler' para {invoice_type}. "
            f"Verifica el XMLID {xmlid} o los códigos {fallback_codes}."
        )
        
    def _get_product_tarifa_alquiler(self, invoice_type='out_invoice'):
        """
        Devuelve product.product (variante) para 'Tarifa de alquiler'.

        Args:
            invoice_type (str): Tipo de factura ('out_invoice' o 'in_invoice')
                               - 'out_invoice': usa product_product_42 (venta)
                               - 'in_invoice': usa product_product_50 (compra)

        - Intenta por XMLID (template -> variant si aplica).
        - Fallback por código/nombre.
        - Tolerante a multi-compañía.
        """
        Product  = self.env['product.product']
        Template = self.env['product.template']

        # 1) Determinar XMLID y códigos según tipo de factura
        if invoice_type == 'in_invoice':
            xmlid = 'industry_real_estate.product_product_50'  # Producto para COMPRAS
            fallback_codes = ['TARIFA_ALQ_COMPRA', 'TARIFA_ALQ']
            _logger.debug("Buscando producto para COMPRA (in_invoice): XMLID=%s", xmlid)
        else:  # out_invoice (default)
            xmlid = 'industry_real_estate.product_product_42'  # Producto para VENTAS
            fallback_codes = ['TARIFA_ALQ_VENTA', 'TARIFA_ALQ']
            _logger.debug("Buscando producto para VENTA (out_invoice): XMLID=%s", xmlid)

        # 2) Por XMLID
        prod = self.env.ref(xmlid, raise_if_not_found=False)

        if prod:
            if prod._name == 'product.template':
                prod = prod.product_variant_id
            if prod and prod.exists():
                # Multi-compañía: preferir producto sin compañía o de la misma
                if prod.company_id and self.env.company and prod.company_id != self.env.company:
                    prod2 = Product.search([
                        ('id', '=', prod.id),
                        '|', ('company_id', '=', False),
                            ('company_id', '=', self.env.company.id)
                    ], limit=1)
                    if prod2:
                        prod = prod2
                _logger.debug("  ✓ Producto encontrado por XMLID: %s (ID: %s)", prod.name, prod.id)
                return prod

        # 3) Fallback por código/nombre
        _logger.debug("  >> XMLID no encontrado, intentando fallback por código...")

        # Construir dominio con múltiples códigos posibles
        domain = []
        for i, code in enumerate(fallback_codes):
            if i > 0:
                domain.insert(0, '|')
            domain.append(('default_code', '=', code))

        # Agregar búsqueda por nombre
        domain.insert(0, '|')
        domain.insert(0, '|')
        domain.extend([
            ('name', 'ilike', 'Rental fee'),
            ('name', 'ilike', 'Tarifa de alquiler')
        ])

        if self.env.company:
            domain += ['|', ('company_id', '=', False),
                            ('company_id', '=', self.env.company.id)]

        prod = Product.search(domain, limit=1)
        if prod:
            _logger.debug("  ✓ Producto encontrado por código/nombre: %s (ID: %s)", prod.name, prod.id)
            return prod

        tmpl = Template.search(domain, limit=1)
        if tmpl:
            prod = tmpl.product_variant_id
            if prod and prod.exists():
                _logger.debug("  ✓ Producto encontrado por template: %s (ID: %s)", prod.name, prod.id)
                return prod

        # 4) No se encontró
        _logger.error("  ✗ No se encontró producto 'Tarifa de alquiler' para %s", invoice_type)
        raise UserError(
            f"No se encontró el producto 'Tarifa de alquiler' para {invoice_type}. "
            f"Verifica el XMLID {xmlid} o los códigos {fallback_codes}."
        )
        
    def action_generate_confirm_contracts(self):
        self.ensure_one()

        _logger.info("=" * 80)
        _logger.info("BOTÓN: action_generate_confirm_contracts presionado para contrato: %s", self.name)
        _logger.info("=" * 80)

        # Validar que el contrato esté firmado
        """ if self.x_custom_state != "contract_signed":
            raise UserError(_("No se puede generar documentos porque el contrato aún no está firmado.")) """

        for contract in self:
            _logger.info("Procesando contrato: %s", contract.name)

            # TRANSACCIÓN ATÓMICA: Si falla algo, se revierte TODO
            _logger.info("  >> Iniciando transacción atómica (savepoint)...")
            with self.env.cr.savepoint():
                try:
                    # Generar facturas (mandato, comisión, compra)
                    _logger.info("  [1/2] Llamando a _generate_all_documents_for_period()...")
                    contract._generate_all_documents_for_period()
                    _logger.info("  [1/2] ✓ _generate_all_documents_for_period() completado")

                    # Generar asientos contables de servicios públicos
                    _logger.info("  [2/2] Llamando a _generate_utility_accounting_entries()...")
                    result = contract._generate_utility_accounting_entries()
                    if result:
                        _logger.info("  [2/2] ✓ _generate_utility_accounting_entries() completado. Asiento: %s", result.name)
                    else:
                        _logger.info("  [2/2] ⊘ _generate_utility_accounting_entries() no generó asiento")

                    _logger.info("  >> ✓ Transacción confirmada (commit)")

                except Exception as e:
                    _logger.error("  >> ✗ Error detectado. Ejecutando ROLLBACK de transacción...")
                    _logger.error("✗ ERROR procesando contrato %s: %s", contract.name, str(e), exc_info=True)
                    _logger.error("  >> Todas las facturas y asientos fueron REVERTIDOS")
                    # El savepoint automáticamente hace rollback al salir del contexto con excepción
                    raise  # Re-lanzar la excepción para mostrar al usuario

        _logger.info("=" * 80)
        _logger.info("BOTÓN: Procesamiento completado para contrato: %s", self.name)
        _logger.info("=" * 80)

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    contract_id = fields.Many2one('x.contract', string="Contrato", ondelete='set null')