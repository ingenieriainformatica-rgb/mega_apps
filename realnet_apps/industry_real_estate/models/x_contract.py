from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.industry_real_estate import const
from odoo.tools.safe_eval import safe_eval
import logging
import re


_logger = logging.getLogger(__name__)

class XContract(models.Model):
    _name = 'x.contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Contrato'
    _rec_name = 'name'
    
    x_custom_state = fields.Selection(const.ESTATES, default='draft', tracking=True)
    # Enlazamos con Odoo Sign
    sign_template_id = fields.Many2one('sign.template', string="Plantilla de firma", required=False)
    sign_request_ids = fields.One2many('sign.request', 'x_contract_id', string='Solicitudes de firma')
    sign_request_id = fields.Many2one('sign.request', string="Solicitud de firma")
    sale_order_id = fields.Many2one('sale.order', ondelete='cascade')
    partner_id = fields.Many2one('res.partner')
    partner_lessor_id = fields.Many2one('res.partner')
    x_guarant_partner_id = fields.Many2one('res.partner')
    sign_state = fields.Selection(related='sign_request_id.state', readonly=True)
    is_signed = fields.Boolean(compute='_compute_is_signed', store=False)
    signed_request_count = fields.Integer(
        string='Firmas completadas',
        compute='_compute_is_signed',
        store=False,
    )
    name = fields.Char('Nombre', required=True, copy=False, default='Nuevo')
    order_id = fields.Many2one('sale.order', string='Contrato')

    # Si prefieres validar por adjunto en Documentos con una etiqueta concreta
    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id',
        domain=lambda self: [('res_model', '=', self._name)],
        string='Adjuntos'
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for rec in recs:
            if rec.name in (False, 'Nuevo', '/'):
                # Genera un nombre amigable; ajusta a tu gusto o usa una secuencia
                rec.name = f"{rec.order_id.name} – {rec.order_id.partner_id.display_name}" if rec.order_id else _("Contrato %s") % rec.id
        return recs

    def write(self, vals):
        res = super().write(vals)
        # Opcional: mantener el nombre sincronizado si cambia el pedido
        for rec in self:
            if not vals.get('name') and rec.order_id and rec.name in (False, 'Nuevo', '/'):
                rec.name = f"{rec.order_id.name} – {rec.order_id.partner_id.display_name}"
        return res
    
    def _next_state(self):
        order = const.FINAL_STATES
        self.ensure_one()
        cur = self.x_custom_state or 'draft'
        try:
            idx = order.index(cur)
        except ValueError:
            return 'contract_signed'
        return order[min(idx+1, len(order)-1)]
    
    def _expected_filename(self, target_state, as_regex=False):
        """Si as_regex=True devuelve patrón regex; si False devuelve el nombre esperado legible."""
        fixed = {
            'contract_signed':  lambda s: r"(?i).*contrato.*\.pdf",
            'pending_delivery': lambda s: r"(?i).*acta.*entrega.*\.pdf",
            'delivered':        lambda s: r"(?i).*paz.*salvo.*\.pdf",
            'pending_receipt':  lambda s: r"(?i).*acta.*recepcion.*\.pdf",
            'received':         lambda s: r"(?i).*paz.*salvo.*\.pdf",
            'done':             lambda s: r"(?i).*acta.*finalizacion.*\.pdf",
        }
        regex = {
            'contract_signed':  r'(?i)^contrato.*\.pdf$',
            'pending_delivery': r'(?i)^acta[_\s-]*[_\s-]*entrega\.pdf$',
            'delivered':        r'(?i)^paz[_\s-]*salvo[_\s-]*entrega\.pdf$',
            'pending_receipt':  r'(?i)^acta[_\s-]*recepcion\.pdf$',
            'received':         r'(?i)^paz[_\s-]*salvo[_\s-]*recepcion\.pdf$',
            'done':             r'(?i)^acta[_\s-]*finalizacion\.pdf$',
        }
        return (regex.get(target_state) if as_regex else
                (fixed.get(target_state)(self) if fixed.get(target_state) else None))
    
    def _check_required_signed_doc(self, target_state):
        self.ensure_one()

        # Patrón base desde tu helper (regex “para PDF”)
        pdf_pat = (self._expected_filename(target_state, as_regex=True) or '').strip()
        print("EXPECTED(PDF)", pdf_pat, "TARGET", target_state)

        if not pdf_pat:
            if target_state != 'draft':
                state_label = dict(self._fields['x_custom_state'].selection).get(target_state, target_state)
                raise UserError(_("En el estado '%s' no hay plantilla configurada.") % state_label)
            return self.env['sign.request']

        # Para reference permitimos .pdf opcional (capturamos y sustituimos si viene anclado)
        # -> convierte r'...\.pdf$' en r'...(?:\.pdf)?$'
        ref_pat = pdf_pat
        # Si el patrón no trae .pdf, lo dejamos igual; si lo trae, lo volvemos opcional.
        ref_pat = re.sub(r'\\\.pdf\$', r'(?:\\.pdf)?$', ref_pat)

        # Compilar patrones (aunque ya uses (?i), sumamos IGNORECASE por seguridad)
        try:
            re_pdf = re.compile(pdf_pat, re.IGNORECASE)
            re_ref = re.compile(ref_pat, re.IGNORECASE)
        except re.error as e:
            raise ValidationError(_("Patrón de nombre inválido para '%s': %s") % (target_state, e))

        # 1) Requests firmados
        reqs = self.sign_request_ids.filtered(lambda r: r.state in ('signed', 'completed'))
        # Debug útil:
        for r in reqs:
            print("REQ:", r.id, r.state, "ref=", (r.reference or ''))

        # 1.a) Match por reference (sin exigir .pdf)
        match = reqs.filtered(lambda r: bool(re_ref.search((r.reference or '').strip())))
        if match:
            return True

        # 2) Si no hubo match por reference, buscamos adjuntos PDF del request
        Att = self.env['ir.attachment'].sudo()
        atts = Att.search([
            ('res_model', '=', 'sign.request'),
            ('res_id', 'in', reqs.ids),
            ('mimetype', 'ilike', 'pdf'),
        ])
        for att in atts:
            att_name = (att.name or '').strip()
            print("ATT:", att.id, att_name)
            if re_pdf.search(att_name):
                return True

        # 3) Sin coincidencias -> error claro
        state_label = dict(self._fields['x_custom_state'].selection).get(target_state, target_state)
        raise ValidationError(_(
            "No puedes pasar el contrato a '%(state)s' porque no se encontró un documento firmado "
            "que coincida con el patrón:\n- Para referencia: %(ref)s\n- Para adjunto PDF: %(pdf)s"
        ) % {'state': state_label, 'ref': ref_pat, 'pdf': pdf_pat})
    
    def name_get(self):
        res = []
        for rec in self:
            if getattr(rec, 'order_id', False):
                # Ejemplo de nombre: S0001 – Consumidor Final
                name = f"{rec.order_id.name} – {rec.order_id.partner_id.display_name}"
            else:
                name = _("Contrato %s") % rec.id
            res.append((rec.id, name))
        return res

    def _merge_action_context(self, action: dict, extra: dict) -> dict:
        """Mezcla el context del action (que puede venir como string) con extra."""
        base_ctx = action.get('context') or {}
        if isinstance(base_ctx, str):
            try:
                base_ctx = safe_eval(base_ctx)
            except Exception:
                base_ctx = {}
        elif not isinstance(base_ctx, dict):
            base_ctx = {}
        action['context'] = {**base_ctx, **(extra or {})}
        return action
    
    def action_request_signature(self, target_state=None, signers=None):
        self.ensure_one()
        if not target_state:
            target_state = self.env.context.get('target_state') or self._next_state()
        
        state_rules = self._state_requirements()
        rule = state_rules.get(target_state or 'draft', {}) 
        template_id = rule.get('sign_template_id') or False
        template = self.env['sign.template'].browse(template_id)        
        # nombre esperado dinámico
        expected = self._expected_filename(target_state) or ''
        pattern  = self._expected_filename(target_state, as_regex=True) or r'^$'
        rx = re.compile(pattern, re.I)
        state_label = dict(self._fields['x_custom_state'].selection).get(target_state, target_state)
        msg = _(
            "No puedes cambiar de estado a '%(state)s', porque no existe el documento firmado requerido. \n"
            "Por favor genera o adjunta la firma correspondiente. \n"
            "El nombre esperado es: %(expected)s"
        ) % {'state': state_label, 'expected': expected}
        
        # ===== Usar el PDF del chatter como documento a firmar =====
        Attachment = self.env['ir.attachment'].sudo()
        atts = Attachment.search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', self.sale_order_id.id),
            ('mimetype', '=', 'application/pdf'),
        ], order='create_date desc', limit=20)

        preview_att = next((a for a in atts if rx.match(a.name or '')), None)
        if not preview_att:
            raise ValidationError(_("No se ha generado el pdf del contrato.\nSeleccione una plantilla de contrato para firmar el documento."))
        # Usa el nombre real del PDF como "Referencia" sugerida
        expected = preview_att.name or expected
        if(expected=='' or expected==None or expected==False):
            raise UserError(msg)
        if preview_att:
            # Si tenías una plantilla base con campos/roles, duplica y reemplaza el PDF
            # company_id = self.sale_order_id.company_id.id if self.sale_order_id else self.env.company.id
            if template:
                template = template.copy({
                    'name': f"{template.name} - {self.name}",
                    'attachment_id': preview_att.id,  # <- usar el PDF del chatter
                    # 'company_id': company_id,
                })
            else:
                # Como último recurso, crear una plantilla mínima desde el adjunto
                # (sin campos predefinidos; podrás arrastrarlos en el diseñador)
                template = self.env['sign.template'].create({
                    'name': f"{expected}",
                    'attachment_id': preview_att.id,
                    # 'company_id': company_id,
                })           
        

        # abre el asistente de envío de firma
        action = self.env['ir.actions.actions']._for_xml_id('sign.action_sign_send_request')
        ctx = action.get('context') or {}
        if isinstance(ctx, str):
            try:
                ctx = safe_eval(ctx)
            except Exception:
                ctx = {}
        
        role_field = None
        items = template.sign_item_ids
        for candidate in ('role_id', 'responsible_id', 'signer_id'):
            if candidate in items._fields:
                role_field = candidate
                break
        if not role_field:
            # si tu plantilla no usa roles por ítem, puedes omitir el mapeo a rol
            _logger.warning("La plantilla %s no expone campo de rol en sign_item_ids.", template.display_name)
            roles = []
        else:
            roles = items.mapped(role_field)
    
        partners  = [] if signers is None else signers
        items_cmds = []
        for partner, role in zip(partners, roles or partners): # si no hay roles, no pases role_id
            vals = {'partner_id': partner.id}
            if role_field and role:
                # el campo de rol en sign.request.item se llama role_id (ahí sí)
                vals['role_id'] = role.id
            items_cmds.append((0, 0, vals))
        ctx.update({
            'default_template_id': template.id,
            'default_reference': expected or '',
            'default_request_item_ids': items_cmds,
            'default_request_item_user_ids': items_cmds,
            'default_x_contract_id': self.id,
        })
        action['context'] = ctx
        _logger.info("CTX BASE: %s", ctx)
        return action

    @api.depends('sign_request_ids.state')
    def _compute_is_signed(self):
        """Marca el contrato como firmado si hay al menos una sign.request en estado final."""
        for rec in self:
            if not rec.exists():
                continue
            signed_reqs = rec.sign_request_ids.filtered(lambda r: r.state in const.FINAL_STATES)
            rec.is_signed = bool(signed_reqs)
            rec.signed_request_count = len(signed_reqs)

    # Acción para abrir la vista del contrato (y desde ahí el flujo de firma)
    def action_open_for_sign(self):
        self.ensure_one()
        # intenta tu vista; si no existe, usa la vista por defecto
        try:
            view = self.env.ref('industry_real_estate.view_x_contract_form')
            views = [(view.id, 'form')]
        except ValueError:
            views = [(False, 'form')]

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'x.contract',
            'res_id': self.id,
            'view_mode': 'form',
            'views': views,
            'target': 'current',
            'context': {
                'default_sale_order_id': self.sale_order_id.id if self.sale_order_id else False,
                'default_partner_id': self.sale_order_id.partner_id.id if self.sale_order_id else False,
            },
        }

    def _state_requirements(self):
        C = self.env.company
        """ 'contract_signed':  lambda s: f"contrato_de_arrendamiento.pdf",
            'pending_delivery': lambda s: f"acta_de_entrega.pdf",
            'delivered':        lambda s: f"paz_y_salvo_entrega.pdf",
            'pending_receipt':  lambda s: f"acta_de_recepcion.pdf",
            'received':         lambda s: f"paz_y_salvo_recepcion.pdf",
            'done':             lambda s: f"acta_de_finalizacion.pdf", """
        return {
            'draft': {'sign_template_id': False, 'require_fully_signed': False, 'format': ''},
            'contract_signed': {
                'sign_template_id': C.sign_template_contract_id.id,
                'require_fully_signed': True,
                'require_partner_id': 'partner_id',
                'format': "contrato_de_arrendamiento.pdf",
            },
            'pending_delivery':{
                'sign_template_id': C.sign_template_delivery_id.id,
                'require_fully_signed': True,
                'require_partner_id': 'partner_id',
                'format': "acta_de_entrega.pdf",
            },
            'delivered': {
                'sign_template_id': C.sign_template_clearance_delivery_id.id,
                'require_fully_signed': True,
                'require_partner_id': 'partner_id',
                'format': "paz_y_salvo_entrega.pdf",
            },
            'pending_receipt': {
                'sign_template_id': C.sign_template_reception_id.id,
                'require_fully_signed': False,
                'require_partner_id': 'partner_id',
                'format': "acta_de_recepcion.pdf",
            },
            'received': {
                'sign_template_id': C.sign_template_clearance_reception_id.id,
                'require_fully_signed': True,
                'require_partner_id': 'partner_id',
                'format': "paz_y_salvo_recepcion.pdf",
            },
            'done': {
                'sign_template_id': C.sign_template_finish_id.id,
                'require_fully_signed': True,
                'require_partner_id': 'partner_id',
                'format': "acta_de_finalizacion.pdf",
            },
        }

    # --- API para cambiar estado con validación centralizada ---
    def action_change_state(self):
        self.ensure_one()
        target_state = self.env.context.get('new_state')
        if not target_state:
            raise UserError(_("Falta definir un estado en el contexto."))        
        if target_state != 'draft':
            if target_state == 'contract_signed':
                self._set_property_availability(available=True) 
            if target_state == 'done':
                self._set_property_availability(available=False) 
            self._check_required_signed_doc(target_state)
        
        self.x_custom_state = target_state
        self.write({'x_custom_state': target_state})
        if self.sale_order_id:
            self.sale_order_id.write({'x_custom_state': target_state})
        
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def _get_ecoerp_settings(self):
        IC = self.env['ir.config_parameter'].sudo()
        admin_pct = float(IC.get_param('eco_erp.default_admin_percent', default=10.0))
        product_canon = self.env['product.product'].browse(int(IC.get_param('eco_erp.product_canon_id') or 0))
        product_owner = self.env['product.product'].browse(int(IC.get_param('eco_erp.product_owner_payment_id') or 0))
        return admin_pct, product_canon, product_owner
    
    def _get_property_account(self):
        """Obtiene la cuenta analítica (propiedad) desde la SO vinculada."""
        self.ensure_one()
        so = self.sale_order_id
        if not so:
            return self.env['account.analytic.account']
        return so.x_account_analytic_account_id  # este es el campo que ya usas en vistas

    def _is_rental(self):
        self.ensure_one()
        so = self.sale_order_id
        return bool(so and getattr(so, 'ecoerp_scope', False) == 'rental')

    def _set_property_availability(self, *, available):
        """Actualiza disponibilidad de la propiedad si aplica (solo contratos de alquiler)."""
        for rec in self:
            if not rec._is_rental():
                continue
            prop = rec._get_property_account()
            if prop:
                prop.sudo().write({'x_is_available': bool(available)})   
