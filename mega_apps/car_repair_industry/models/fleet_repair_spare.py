# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

AVAILABILITY_SELECTION = [
    ('in_stock', 'En stock'),
    ('to_order', 'Por confirmar'),
    ('out_of_stock', 'Agotado'),
    ('replaced', 'Reemplazado'),
]


class FleetRepairSpareCatalog(models.Model):
    _name = 'fleet.repair.spare.catalog'
    _description = 'Catálogo de repuestos genéricos'
    _order = 'name asc'
    _rec_name = 'name'

    name = fields.Char(string='Nombre del repuesto', required=True, index=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        (
            'name_unique',
            'unique(name)',
            'Ya existe un repuesto con este nombre en el catálogo.',
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name'):
                vals['name'] = vals['name'].strip().upper()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('name'):
            vals['name'] = vals['name'].strip().upper()
        return super().write(vals)

    @api.constrains('name')
    def _check_name_not_empty(self):
        for rec in self:
            if not (rec.name or '').strip():
                raise ValidationError(_("El nombre del repuesto no puede estar vacío."))


class FleetRepairSpareRequest(models.Model):
    _name = 'fleet.repair.spare.request'
    _description = 'Solicitud de repuestos para cotizar'
    _order = 'request_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ── Campos originales del técnico ──────────────────────────────────────

    repair_id = fields.Many2one(
        'fleet.repair',
        string='Orden de taller',
        required=True,
        ondelete='cascade',
        index=True,
    )
    repair_sequence = fields.Char(
        related='repair_id.sequence', string='# Orden', store=False,
    )
    requested_by_id = fields.Many2one(
        'res.users',
        string='Técnico solicitante',
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
    )
    request_date = fields.Datetime(
        string='Fecha de solicitud',
        default=fields.Datetime.now,
        readonly=True,
    )
    state = fields.Selection(
        [
            ('requested', 'Solicitado'),
            ('in_progress', 'Cotizando'),
            ('ready', 'Lista para crear'),
            ('quoted', 'Cotización creada'),
            ('cancelled', 'Cancelada'),
        ],
        string='Estado',
        default='requested',
        required=True,
        tracking=True,
        copy=False,
    )
    warehouse_note = fields.Text(string='Observación de almacén')
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        index=True,
    )
    line_ids = fields.One2many(
        'fleet.repair.spare.request.line',
        'request_id',
        string='Repuestos solicitados',
    )
    line_count = fields.Integer(
        string='Cant. repuestos',
        compute='_compute_line_count',
        store=True,
    )

    # ── Campos relacionados del técnico (solo lectura) ─────────────────────

    client_id = fields.Many2one(
        'res.partner',
        related='repair_id.client_id',
        string='Cliente',
        store=False,
    )
    vehicle_plate = fields.Char(
        related='repair_id.license_plate',
        string='Placa',
        store=False,
    )
    vehicle_model_id = fields.Many2one(
        'fleet.vehicle.model',
        related='repair_id.model_id',
        string='Modelo',
        store=False,
    )
    vehicle_brand_id = fields.Many2one(
        'fleet.vehicle.model.brand',
        related='repair_id.vehicle_brand_id',
        string='Marca',
        store=False,
    )
    customer_type = fields.Selection(
        related='repair_id.customer_type',
        string='Sede',
        store=False,
    )

    # ── Campos del Cotizador (cabecera) ────────────────────────────────────

    quoter_user_id = fields.Many2one(
        'res.users',
        string='Cotizador responsable',
        tracking=True,
        copy=False,
        index=True,
    )
    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Lista de precios',
        tracking=True,
        copy=False,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        compute='_compute_currency_id',
        store=True,
        readonly=True,
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Almacén',
        copy=False,
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Cotización oficial',
        copy=False,
        readonly=True,
        tracking=True,
    )
    so_out_of_sync = fields.Boolean(
        string='Cotización desactualizada',
        default=False,
        copy=False,
    )
    note_commercial = fields.Text(
        string='Nota comercial para el cliente',
    )

    # ── Totales calculados ─────────────────────────────────────────────────

    amount_untaxed = fields.Monetary(
        string='Subtotal',
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True,
    )
    amount_discount = fields.Monetary(
        string='Descuentos',
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True,
    )
    amount_tax = fields.Monetary(
        string='Impuestos',
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True,
    )
    amount_total = fields.Monetary(
        string='Total cotizado',
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True,
    )

    # ── Contadores stat buttons ────────────────────────────────────────────

    quotation_count = fields.Integer(
        string='Cotizaciones',
        compute='_compute_quotation_count',
    )

    # ── Cómputos ──────────────────────────────────────────────────────────

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.depends('pricelist_id', 'company_id')
    def _compute_currency_id(self):
        for req in self:
            req.currency_id = (
                req.pricelist_id.currency_id
                if req.pricelist_id
                else req.company_id.currency_id
            )

    @api.depends(
        'line_ids.price_subtotal',
        'line_ids.price_tax',
        'line_ids.qty_quoted',
        'line_ids.price_unit',
        'line_ids.discount',
    )
    def _compute_amounts(self):
        for req in self:
            untaxed = sum(req.line_ids.mapped('price_subtotal'))
            tax = sum(req.line_ids.mapped('price_tax'))
            discount = 0.0
            for line in req.line_ids:
                if line.discount and line.qty_quoted and line.price_unit:
                    gross = line.qty_quoted * line.price_unit
                    net = gross * (1.0 - line.discount / 100.0)
                    discount += gross - net
            req.amount_untaxed = untaxed
            req.amount_tax = tax
            req.amount_total = untaxed + tax
            req.amount_discount = discount

    def _compute_quotation_count(self):
        for req in self:
            req.quotation_count = 1 if req.sale_order_id else 0

    # ── Helper: almacén por sede ───────────────────────────────────────────

    def _get_warehouse_from_repair(self, repair=None):
        """Devuelve el warehouse configurado para la sede de la reparación.

        Acepta `repair` explícito para poder usarse en create() antes de que
        self.repair_id esté disponible.  Devuelve un recordset vacío si la sede
        no tiene almacén configurado o si no existe una rama para ese customer_type.
        """
        r = repair if repair else (self.repair_id if self else self.env['fleet.repair'])
        if not r or not r.customer_type:
            return self.env['stock.warehouse']
        branch = self.env['fleet.repair.branch'].search(
            [('customer_type', '=', r.customer_type)], limit=1
        )
        return branch.warehouse_id if branch and branch.warehouse_id else self.env['stock.warehouse']

    # ── Creación con almacén automático ───────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('warehouse_id') and vals.get('repair_id'):
                repair = self.env['fleet.repair'].browse(vals['repair_id'])
                wh = self._get_warehouse_from_repair(repair=repair)
                if wh:
                    vals['warehouse_id'] = wh.id
            if not vals.get('pricelist_id') and vals.get('repair_id'):
                repair = self.env['fleet.repair'].browse(vals['repair_id'])
                pl = repair.client_id.property_product_pricelist if repair.client_id else False
                if pl:
                    vals['pricelist_id'] = pl.id
        return super().create(vals_list)

    # ── Onchanges ─────────────────────────────────────────────────────────

    @api.onchange('repair_id')
    def _onchange_repair_id(self):
        if self.repair_id and not self.pricelist_id:
            partner = self.repair_id.client_id
            if partner:
                self.pricelist_id = partner.property_product_pricelist
        # Rellenar almacén desde la sede; no sobreescribir si ya fue elegido manualmente
        if self.repair_id and not self.warehouse_id:
            wh = self._get_warehouse_from_repair()
            if wh:
                self.warehouse_id = wh

    # ── Transiciones de estado ─────────────────────────────────────────────

    def action_take_request(self):
        """Cotizador toma la solicitud: requested → in_progress."""
        self._check_quoter_access()
        for rec in self:
            if rec.state not in ('requested',):
                raise UserError(_(
                    "Solo se puede tomar una solicitud en estado 'Solicitado'. "
                    "Estado actual: %s"
                ) % dict(self._fields['state'].selection).get(rec.state, rec.state))
            vals = {'state': 'in_progress'}
            if not rec.quoter_user_id:
                vals['quoter_user_id'] = self.env.user.id
            if not rec.pricelist_id and rec.repair_id.client_id:
                vals['pricelist_id'] = (
                    rec.repair_id.client_id.property_product_pricelist.id or False
                )
            rec.write(vals)
            rec.message_post(
                body=_("Solicitud tomada por %s.") % self.env.user.name,
            )
        return True

    def action_mark_ready(self):
        """Cotizador marca la solicitud como lista: in_progress → ready."""
        self._check_quoter_access()
        for rec in self:
            if rec.state not in ('in_progress',):
                raise UserError(_(
                    "Solo se puede marcar lista una solicitud 'Cotizando'. "
                    "Estado actual: %s"
                ) % dict(self._fields['state'].selection).get(rec.state, rec.state))
            rec._validate_ready_to_quote()
            rec.write({'state': 'ready'})
        return True

    def action_mark_reviewed(self):
        """Compatibilidad: igual a marcar lista."""
        return self.action_mark_ready()

    def action_back_to_in_progress(self):
        """Retroceder de 'Lista para crear' → 'Cotizando' para corregir líneas."""
        self._check_quoter_access()
        for rec in self:
            if rec.state != 'ready':
                raise UserError(_(
                    "Solo se puede retroceder desde el estado 'Lista para crear'. "
                    "Estado actual: %s"
                ) % dict(self._fields['state'].selection).get(rec.state, rec.state))
            if rec.sale_order_id:
                raise UserError(_(
                    "No se puede retroceder porque ya existe la cotización vinculada %s."
                ) % rec.sale_order_id.name)
            rec.write({'state': 'in_progress'})
            rec.message_post(body=_("Solicitud devuelta a 'Cotizando' para revisión."))
        return True

    def button_cancel(self):
        """Cancelar solicitud."""
        for rec in self:
            if rec.state == 'quoted' and rec.sale_order_id:
                raise UserError(_(
                    "Esta solicitud tiene una cotización vinculada (%s). "
                    "Cancele primero la cotización en Ventas antes de cancelar la solicitud."
                ) % rec.sale_order_id.name)
            rec.write({'state': 'cancelled'})
        return True

    def button_draft(self):
        """Volver a borrador (solo admin)."""
        for rec in self:
            rec.write({'state': 'requested'})
        return True

    # ── Validación antes de crear cotización ──────────────────────────────

    def _validate_ready_to_quote(self):
        """Valida que las líneas y la cabecera estén listas para generar un sale.order."""
        self.ensure_one()

        # Cliente
        if not self.repair_id.client_id:
            raise UserError(_(
                "La orden de taller no tiene cliente asignado. "
                "Asígnelo antes de crear la cotización."
            ))

        # Lista de precios / moneda
        if not self.pricelist_id:
            raise UserError(_(
                "Debe seleccionar una lista de precios antes de continuar."
            ))

        # Almacén — bloquear aquí (no en la creación de la solicitud)
        if not self.warehouse_id:
            wh = self._get_warehouse_from_repair()
            if not wh:
                customer_type = self.repair_id.customer_type or ''
                sede_label = dict(
                    self.repair_id._fields['customer_type'].selection
                ).get(customer_type, customer_type) if customer_type else _('desconocida')
                raise UserError(_(
                    'No se encontró un almacén configurado para la sede "%s". '
                    'Configure el almacén en '
                    'Taller de autos → Configuración → Sedes y almacenes '
                    'antes de crear la cotización.'
                ) % sede_label)

        # Líneas con producto
        lines = self.line_ids.filtered(lambda l: l.product_id)
        if not lines:
            raise UserError(_(
                "No hay ninguna línea con producto seleccionado. "
                "El Cotizador debe completar al menos una línea con producto y cantidad."
            ))

        # Cantidad
        zero_qty = lines.filtered(lambda l: not l.qty_quoted or l.qty_quoted <= 0)
        if zero_qty:
            raise UserError(_(
                "Las siguientes líneas tienen cantidad cero o vacía:\n%s\n"
                "Corrija las cantidades antes de continuar."
            ) % '\n'.join('- ' + (l.spare_catalog_id.name or l.commercial_description or '') for l in zero_qty))

        # Precio
        zero_price = lines.filtered(lambda l: l.qty_quoted > 0 and l.price_unit <= 0)
        if zero_price:
            raise UserError(_(
                "Las siguientes líneas tienen precio cero:\n%s\n"
                "Ingrese un precio válido antes de continuar."
            ) % '\n'.join('- ' + (l.product_id.display_name or '') for l in zero_price))

    # ── Creación del sale.order ────────────────────────────────────────────

    def action_create_quotation_for_client(self):
        """Crear un sale.order desde esta solicitud de repuestos."""
        self.ensure_one()
        self._check_quoter_access()

        if self.state != 'ready':
            raise UserError(_(
                "La solicitud debe estar en estado 'Lista para crear' antes de generar la cotización."
            ))

        self._validate_ready_to_quote()

        # ── Ya existe SO propio ──
        if self.sale_order_id:
            so = self.sale_order_id
            if so.state == 'draft':
                raise UserError(_(
                    'Esta solicitud ya tiene la cotización %s. '
                    'Use "Ver cotización" para abrirla o "Actualizar cotización" si cambió algo.'
                ) % so.name)
            raise UserError(_(
                'La cotización vinculada (%s) está en estado "%s". '
                'No puede modificarse automáticamente. '
                'Gestione la situación desde el módulo de Ventas.'
            ) % (so.name, dict(so._fields['state'].selection).get(so.state, so.state)))

        # ── Cross-check: la reparación ya tiene SO de otro origen (ej. diagnóstico) ──
        repair_so = self.repair_id.sale_order_id if self.repair_id else False
        if repair_so and repair_so != self.sale_order_id:
            if repair_so.state == 'draft':
                raise UserError(_(
                    'La orden de taller ya tiene la cotización %s en borrador '
                    '(creada desde el diagnóstico). '
                    'Para agregar estos repuestos, ábrala directamente en Ventas '
                    'o cancele esa cotización primero.'
                ) % repair_so.name)
            if repair_so.state in ('sale', 'done'):
                raise UserError(_(
                    'La orden de taller ya tiene la cotización %s confirmada. '
                    'No se puede crear otra cotización para la misma reparación.'
                ) % repair_so.name)
            # Si está cancelada, se puede continuar creando una nueva.

        # ── Asegurar almacén (fallback final antes de crear SO) ──
        if not self.warehouse_id:
            wh = self._get_warehouse_from_repair()
            if wh:
                self.write({'warehouse_id': wh.id})

        # ── Crear el SO ──
        order = self.env['sale.order'].create(self._prepare_sale_order_vals())

        for line in self.line_ids.filtered(lambda l: l.product_id and l.qty_quoted > 0):
            sol = self.env['sale.order.line'].create(
                line._prepare_sale_order_line_vals(order)
            )
            line.write({'sale_line_id': sol.id})

        self.write({
            'sale_order_id': order.id,
            'state': 'quoted',
            'so_out_of_sync': False,
        })

        # Actualizar sale_order_id en la reparación si aún no está establecido
        if self.repair_id and not self.repair_id.sale_order_id:
            self.repair_id.write({'sale_order_id': order.id})

        # Actualizar flujo operativo
        if self.repair_id:
            try:
                self.repair_id.write({'service_flow_state': 'quote_ready'})
            except Exception:
                pass

        self.message_post(
            body=_('Cotización oficial creada: <a href="/odoo/sales/%d">%s</a> por %s.') % (
                order.id, order.name, self.env.user.name,
            ),
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cotización creada'),
                'message': _('Cotización %s creada exitosamente.') % order.name,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_update_quotation(self):
        """Actualizar las líneas del SO existente con los valores actuales."""
        self.ensure_one()
        self._check_quoter_access()

        so = self.sale_order_id
        if not so:
            raise UserError(_('No existe cotización vinculada a esta solicitud.'))
        if so.state not in ('draft',):
            raise UserError(_(
                'Solo se puede actualizar una cotización en borrador. '
                'La cotización %s está en estado "%s".'
            ) % (so.name, so.state))

        self._validate_ready_to_quote()

        # Eliminar líneas del SO que provienen de esta solicitud
        lines_to_remove = so.order_line.filtered(
            lambda l: l.spare_request_line_id and
                      l.spare_request_line_id.request_id.id == self.id
        )
        lines_to_remove.unlink()

        # Limpiar referencias en las líneas de solicitud
        self.line_ids.write({'sale_line_id': False})

        # Recrear líneas
        for line in self.line_ids.filtered(lambda l: l.product_id and l.qty_quoted > 0):
            sol = self.env['sale.order.line'].create(
                line._prepare_sale_order_line_vals(so)
            )
            line.write({'sale_line_id': sol.id})

        self.write({'so_out_of_sync': False})
        self.message_post(
            body=_('Cotización %s actualizada con los valores actuales de la solicitud.') % so.name,
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cotización actualizada'),
                'message': _('Cotización %s actualizada.') % so.name,
                'type': 'success',
                'sticky': False,
            },
        }

    def _prepare_sale_order_vals(self):
        """Preparar los valores para crear el sale.order."""
        self.ensure_one()
        repair = self.repair_id
        return {
            'partner_id': repair.client_id.id,
            'state': 'draft',
            'fleet_repair_id': repair.id,
            'diagnose_id': repair.diagnose_id.id if repair.diagnose_id else False,
            'vehicle_plate': repair.license_plate or '',
            'vehicle_model_id': repair.model_id.id if repair.model_id else False,
            'pricelist_id': self.pricelist_id.id if self.pricelist_id else False,
            'warehouse_id': self.warehouse_id.id if self.warehouse_id else False,
            'note': self.note_commercial or '',
            'spare_request_id': self.id,
        }

    # ── Botón ver cotización ───────────────────────────────────────────────

    def action_view_quotation(self):
        """Abrir el sale.order vinculado."""
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_('No existe cotización vinculada.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cotización'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
        }

    # ── Envío por correo ───────────────────────────────────────────────────

    def action_send_by_email(self):
        """Abrir el compositor estándar de cotización del SO vinculado."""
        self.ensure_one()
        so = self._get_quotation_or_raise()
        template = self.env.ref('sale.email_template_edi_sale', raise_if_not_found=False)
        ctx = {
            'default_model': 'sale.order',
            'default_res_ids': [so.id],
            'default_use_template': bool(template),
            'default_template_id': template.id if template else False,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    # ── Envío por WhatsApp ─────────────────────────────────────────────────

    def action_send_by_whatsapp(self):
        """Abrir el wizard de WhatsApp del SO vinculado (requiere módulo whatsapp)."""
        self.ensure_one()
        so = self._get_quotation_or_raise()

        # Verificar teléfono del cliente
        partner = so.partner_id
        phone = partner.phone or partner.mobile
        if not phone:
            raise UserError(_(
                'El cliente "%s" no tiene teléfono ni celular registrado. '
                'Actualice el contacto antes de enviar por WhatsApp.'
            ) % partner.name)

        # Usar el wizard nativo de WhatsApp si está disponible
        if self.env['ir.model'].sudo().search([('model', '=', 'whatsapp.composer')], limit=1):
            template = self.env['whatsapp.template'].sudo().search([
                ('model', '=', 'sale.order'),
                ('status', '=', 'approved'),
            ], limit=1)
            ctx = {
                'default_res_model': 'sale.order',
                'default_res_ids': [so.id],
            }
            if template:
                ctx['default_wa_template_id'] = template.id
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'whatsapp.composer',
                'view_mode': 'form',
                'target': 'new',
                'context': ctx,
            }

        # Fallback: generar URL wa.me
        import urllib.parse
        msg = _('Hola %s, le enviamos la cotización %s. Placa: %s.') % (
            partner.name, so.name, so.vehicle_plate or '',
        )
        wa_url = 'https://wa.me/%s?text=%s' % (
            (phone or '').replace('+', '').replace(' ', ''),
            urllib.parse.quote(msg),
        )
        return {
            'type': 'ir.actions.act_url',
            'url': wa_url,
            'target': 'new',
        }

    def action_send_by_both(self):
        """Guiar al usuario para enviar por correo Y WhatsApp."""
        self.ensure_one()
        # Primero abrir correo; al cerrar el usuario puede presionar WhatsApp
        return self.action_send_by_email()

    # ── Helpers ────────────────────────────────────────────────────────────

    def _get_quotation_or_raise(self):
        if not self.sale_order_id:
            raise UserError(_('Primero debe crear la cotización oficial.'))
        return self.sale_order_id

    def _check_quoter_access(self):
        """Verificar que el usuario tiene permiso de Cotizador, Supervisor o Admin."""
        user = self.env.user
        allowed = (
            user.has_group('car_repair_industry.group_fleet_repair_portal_quoter')
            or user.has_group('car_repair_industry.group_fleet_repair_spare_warehouse')
            or user.has_group('car_repair_industry.group_fleet_repair_service_manager')
            or user.has_group('base.group_system')
        )
        if not allowed:
            raise UserError(_(
                'No tiene permiso para realizar esta acción. '
                'Se requiere el rol Cotizador, Almacén, Supervisor o Administrador.'
            ))

    # ── Seguimiento de sincronización ─────────────────────────────────────

    @api.onchange('line_ids')
    def _onchange_line_ids_sync(self):
        """Marcar desincronizado si se modifican líneas después de crear la cotización."""
        if self.sale_order_id and self.state == 'quoted':
            self.so_out_of_sync = True


class FleetRepairSpareRequestLine(models.Model):
    _name = 'fleet.repair.spare.request.line'
    _description = 'Línea de solicitud de repuesto'
    _order = 'id asc'

    # ── Campos originales del técnico ──────────────────────────────────────

    request_id = fields.Many2one(
        'fleet.repair.spare.request',
        string='Solicitud',
        required=True,
        ondelete='cascade',
        index=True,
    )
    spare_catalog_id = fields.Many2one(
        'fleet.repair.spare.catalog',
        string='Repuesto solicitado',
        required=True,
    )
    quantity = fields.Float(
        string='Cant. solicitada',
        required=True,
        default=1.0,
    )
    technician_note = fields.Text(string='Observación del técnico')
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        related='request_id.company_id',
        store=True,
    )

    # ── Moneda (del encabezado) ────────────────────────────────────────────

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='request_id.currency_id',
        store=True,
    )

    # ── Campos comerciales del Cotizador ──────────────────────────────────

    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        domain=[('sale_ok', '=', True)],
        index=True,
    )
    commercial_description = fields.Text(
        string='Descripción comercial',
    )
    qty_quoted = fields.Float(
        string='Cant. cotizada',
        digits='Product Unit of Measure',
        default=0.0,
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unidad de medida',
    )
    price_unit = fields.Monetary(
        string='Precio unitario',
        currency_field='currency_id',
        default=0.0,
    )
    discount = fields.Float(
        string='Desc. %',
        digits=(5, 2),
        default=0.0,
    )
    tax_ids = fields.Many2many(
        'account.tax',
        'spare_req_line_tax_rel',
        'line_id',
        'tax_id',
        string='Impuestos',
        domain=[('type_tax_use', '=', 'sale')],
    )
    availability_state = fields.Selection(
        AVAILABILITY_SELECTION,
        string='Disponibilidad',
    )
    internal_quote_note = fields.Text(string='Nota interna')
    customer_note = fields.Text(string='Nota para el cliente')

    # ── Subtotales calculados ──────────────────────────────────────────────

    price_subtotal = fields.Monetary(
        string='Subtotal',
        currency_field='currency_id',
        compute='_compute_price_subtotal',
        store=True,
    )
    price_tax = fields.Monetary(
        string='Impuestos calc.',
        currency_field='currency_id',
        compute='_compute_price_subtotal',
        store=True,
    )
    price_total = fields.Monetary(
        string='Total',
        currency_field='currency_id',
        compute='_compute_price_subtotal',
        store=True,
    )

    # ── Trazabilidad hacia sale.order.line ────────────────────────────────

    sale_line_id = fields.Many2one(
        'sale.order.line',
        string='Línea de cotización',
        copy=False,
        readonly=True,
        ondelete='set null',
        index=True,
    )

    # ── Cómputos ──────────────────────────────────────────────────────────

    @api.depends('qty_quoted', 'price_unit', 'discount', 'tax_ids', 'currency_id', 'product_id')
    def _compute_price_subtotal(self):
        for line in self:
            if not line.qty_quoted or not line.price_unit:
                line.price_subtotal = 0.0
                line.price_tax = 0.0
                line.price_total = 0.0
                continue

            base = line.qty_quoted * line.price_unit * (1.0 - (line.discount or 0.0) / 100.0)

            if line.tax_ids:
                taxes = line.tax_ids.compute_all(
                    base,
                    currency=line.currency_id or line.request_id.company_id.currency_id,
                    quantity=1.0,
                    product=line.product_id,
                    partner=line.request_id.client_id,
                )
                line.price_subtotal = taxes['total_excluded']
                line.price_total = taxes['total_included']
                line.price_tax = taxes['total_included'] - taxes['total_excluded']
            else:
                line.price_subtotal = base
                line.price_total = base
                line.price_tax = 0.0

    # ── Onchanges ─────────────────────────────────────────────────────────

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        product = self.product_id
        req = self.request_id

        # Descripción comercial
        self.commercial_description = product.get_product_multiline_description_sale() \
            if hasattr(product, 'get_product_multiline_description_sale') \
            else product.display_name

        # Unidad de medida
        self.product_uom_id = product.uom_id

        # Cantidad cotizada: si el técnico pidió una cantidad, usarla como default
        if not self.qty_quoted or self.qty_quoted == 0:
            self.qty_quoted = self.quantity or 1.0

        # Impuestos
        company = req.company_id or self.env.company
        self.tax_ids = product.taxes_id.filtered(
            lambda t: t.company_id == company
        )

        # Precio según lista de precios
        pricelist = req.pricelist_id
        partner = req.client_id
        qty = self.qty_quoted or 1.0

        if pricelist:
            try:
                price = pricelist._get_product_price(
                    product, qty, currency=pricelist.currency_id, date=fields.Date.today()
                )
            except Exception:
                price = product.lst_price
        else:
            price = product.lst_price

        self.price_unit = price

    @api.onchange('qty_quoted')
    def _onchange_qty_quoted(self):
        """Actualizar precio si cambia la cantidad (puede afectar escalonado de precios)."""
        if not self.product_id or not self.qty_quoted:
            return
        req = self.request_id
        pricelist = req.pricelist_id
        if pricelist:
            try:
                price = pricelist._get_product_price(
                    self.product_id, self.qty_quoted,
                    currency=pricelist.currency_id, date=fields.Date.today()
                )
                self.price_unit = price
            except Exception:
                pass

    @api.constrains('quantity')
    def _check_quantity(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError(_("La cantidad solicitada debe ser mayor que cero."))

    # ── Preparar vals para sale.order.line ────────────────────────────────

    def _prepare_sale_order_line_vals(self, order):
        """Preparar los valores para crear sale.order.line desde esta línea."""
        self.ensure_one()
        description = (
            self.commercial_description
            or self.product_id.display_name
            or self.spare_catalog_id.name
        )
        if self.customer_note:
            description = '%s\n%s' % (description, self.customer_note)
        return {
            'order_id': order.id,
            'product_id': self.product_id.id,
            'name': description,
            'product_uom_qty': self.qty_quoted,
            'product_uom': self.product_uom_id.id or self.product_id.uom_id.id,
            'price_unit': self.price_unit,
            'discount': self.discount,
            'tax_id': [(6, 0, self.tax_ids.ids)],
            'spare_request_line_id': self.id,
        }


class FleetRepairSpareExt(models.Model):
    """Extiende fleet.repair con la relación de solicitudes de repuestos."""
    _inherit = 'fleet.repair'

    spare_request_ids = fields.One2many(
        'fleet.repair.spare.request',
        'repair_id',
        string='Solicitudes de repuestos',
    )
    spare_request_count = fields.Integer(
        string='Solicitudes repuestos',
        compute='_compute_spare_request_count',
        store=True,
    )

    @api.depends('spare_request_ids')
    def _compute_spare_request_count(self):
        for rec in self:
            rec.spare_request_count = len(rec.spare_request_ids)

    def action_view_spare_requests(self):
        self.ensure_one()
        return {
            'name': _('Solicitudes de repuestos'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.repair.spare.request',
            'view_mode': 'list,form',
            'domain': [('repair_id', '=', self.id)],
            'context': {'default_repair_id': self.id},
        }


class SaleOrderSpareExt(models.Model):
    """Añade el enlace de vuelta a la solicitud de repuestos en sale.order."""
    _inherit = 'sale.order'

    spare_request_id = fields.Many2one(
        'fleet.repair.spare.request',
        string='Solicitud de repuestos origen',
        copy=False,
        readonly=True,
        index=True,
    )


class SaleOrderLineSpareExt(models.Model):
    """Añade trazabilidad desde sale.order.line hacia spare.request.line."""
    _inherit = 'sale.order.line'

    spare_request_line_id = fields.Many2one(
        'fleet.repair.spare.request.line',
        string='Línea de solicitud origen',
        copy=False,
        ondelete='set null',
        index=True,
    )
