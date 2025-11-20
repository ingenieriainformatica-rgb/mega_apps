from datetime import datetime, timedelta
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PosReservation(models.Model):
    _name = 'pos.reservation'
    _description = 'POS Reservation (Layaway)'
    _order = 'id desc'

    name = fields.Char(string='Referencia', default=lambda self: self._default_name(), copy=False, index=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Tarifa')
    pos_config_id = fields.Many2one('pos.config', string='Config POS', required=True)
    pos_session_id = fields.Many2one('pos.session', string='Sesión POS')
    user_id = fields.Many2one('res.users', string='Vendedor', default=lambda self: self.env.user)
    date_reservation = fields.Datetime(string='Fecha de Apartado', default=fields.Datetime.now)
    expiration_date = fields.Date(string='Fecha de Vencimiento', compute='_compute_expiration', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, readonly=True)
    amount_total = fields.Monetary(string='Total', compute='_compute_amounts', store=True)
    amount_paid = fields.Monetary(string='Pagado', compute='_compute_amounts', store=True)
    amount_due = fields.Monetary(string='Saldo', compute='_compute_amounts', store=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('reserved', 'Reservado'),
        ('paid', 'Pagado'),
        ('invoiced', 'Facturado'),
        ('expired', 'Vencido'),
        ('cancelled', 'Cancelado'),
    ], default='reserved', index=True)
    note = fields.Text()
    line_ids = fields.One2many('pos.reservation.line', 'reservation_id', string='Líneas')
    payment_ids = fields.One2many('pos.reservation.payment', 'reservation_id', string='Abonos')
    invoice_id = fields.Many2one('account.move', string='Factura')
    allow_refund = fields.Boolean(default=False)
    hold_ids = fields.One2many('stock.reservation.hold', 'reservation_id', string='Holds')
    company_id = fields.Many2one('res.company', related='pos_config_id.company_id', store=True, readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Movimiento de Reserva', copy=False)
    final_picking_id = fields.Many2one('stock.picking', string='Movimiento de Entrega', copy=False) # Campo añadido para trazabilidad

    def _default_name(self):
        return self.env['ir.sequence'].next_by_code('pos.reservation') or _('POS-RES')

    @api.depends('date_reservation')
    def _compute_expiration(self):
        param_days = int(self.env['ir.config_parameter'].sudo().get_param('pos_reservation_layaway.expiration_days', 90))
        for rec in self:
            base = rec.date_reservation or fields.Datetime.now()
            rec.expiration_date = (base + timedelta(days=param_days)).date()

    @api.depends('line_ids.price_subtotal', 'payment_ids.state', 'payment_ids.amount')
    def _compute_amounts(self):
        for rec in self:
            total = sum(rec.line_ids.mapped('price_subtotal'))
            paid = sum(rec.payment_ids.filtered(lambda p: p.state == 'posted').mapped('amount'))
            rec.amount_total = total
            rec.amount_paid = paid
            rec.amount_due = max(total - paid, 0.0)
            if rec.state not in ('expired', 'cancelled', 'invoiced'):
                rec.state = 'paid' if paid >= total and total > 0 else 'reserved'

    # Business API exposed to POS (via ORM call)
    @api.model
    def create_from_pos(self, payload):
        """payload keys expected:
        partner_id, pricelist_id, pos_config_id, pos_session_id, user_id,
        lines: [{product_id, qty, price_unit, discount, name}],
        initial_payment: {amount, journal_id, ref}
        """
        if not payload:
            raise UserError(_('Sin datos para crear el apartado.'))
        partner_id = payload.get('partner_id')
        pos_config_id = payload.get('pos_config_id')
        session_id = payload.get('pos_session_id')
        user_id = payload.get('user_id') or self.env.user.id
        lines = payload.get('lines') or []
        if not partner_id:
            raise UserError(_('Debe seleccionar un cliente.'))
        if not pos_config_id:
            raise UserError(_('Falta la configuración de POS.'))
        if not lines:
            raise UserError(_('No hay líneas de productos.'))

        # Totals from frozen prices
        total = 0.0
        for l in lines:
            qty = float(l.get('qty') or 0)
            price = float(l.get('price_unit') or 0)
            disc = float(l.get('discount') or 0)
            subtotal = qty * price * (1 - disc / 100.0)
            total += subtotal
        min_percent = float(self.env['ir.config_parameter'].sudo().get_param('pos_reservation_layaway.min_percent', 20.0))
        initial = payload.get('initial_payment') or {}
        initial_amount = float(initial.get('amount') or 0.0)
        min_required = total * (min_percent / 100.0)
        if initial_amount + 1e-6 < min_required:
            raise ValidationError(_("El abono inicial debe ser al menos %.2f%% (%.2f)." % (min_percent, min_required)))

        # Create reservation
        reservation = self.create({
            'partner_id': partner_id,
            'pricelist_id': payload.get('pricelist_id'),
            'pos_config_id': pos_config_id,
            'pos_session_id': session_id,
            'user_id': user_id,
            'state': 'reserved',
            'note': payload.get('note') or '',
        })

        # Lines with frozen price
        Line = self.env['pos.reservation.line']
        for l in lines:
            Line.create({
                'reservation_id': reservation.id,
                'product_id': l['product_id'],
                'name': l.get('name') or self.env['product.product'].browse(l['product_id']).display_name,
                'qty': l.get('qty') or 1.0,
                'price_unit_fixed': l.get('price_unit') or 0.0,
                'discount': l.get('discount') or 0.0,
            })

        # Create holds (custom model)
        hold_location_id = self.env['ir.config_parameter'].sudo().get_param('pos_reservation_layaway.hold_location_id')
        hold_location_id = int(hold_location_id) if hold_location_id else False
        Hold = self.env['stock.reservation.hold']
        for line in reservation.line_ids:
            Hold.create({
                'product_id': line.product_id.id,
                'location_id': hold_location_id or self._default_hold_location(reservation),
                'qty_reserved': line.qty,
                'reservation_id': reservation.id,
                'state': 'active',
            })

        # Create a stock picking to physically reserve quantities in stock (Internal Transfer)
        try:
            picking = self._create_reservation_picking(reservation)
            reservation.picking_id = picking.id
            _logger.info('Layaway %s: created picking %s (state=%s)', reservation.name, getattr(picking, 'name', picking.id), picking.state)
        except Exception as e:
            _logger.error('Layaway %s: failed creating picking: %s', reservation.name, e)
            raise

        # Register initial payment as credit
        if initial_amount > 0:
            self._create_payment(reservation, initial_amount, initial.get('journal_id'), initial.get('ref'))

        reservation._compute_amounts()
        return {
            'id': reservation.id,
            'name': reservation.name,
            'expiration_date': str(reservation.expiration_date),
            'amount_total': reservation.amount_total,
            'amount_paid': reservation.amount_paid,
            'amount_due': reservation.amount_due,
        }

    @api.model
    def add_payment(self, reservation_id, payload):
        reservation = self.browse(reservation_id)
        if not reservation:
            raise UserError(_('Reserva no encontrada.'))
        if reservation.state in ('paid', 'cancelled'):
            raise UserError(_('No se puede abonar en el estado actual.'))

        amount = float(payload.get('amount') or 0.0)
        if amount <= 0:
            raise ValidationError(_('El abono debe ser mayor a 0.'))
        line_id = payload.get('line_id')
        journal_id = payload.get('journal_id')
        pay = self._create_payment(reservation, amount, journal_id, payload.get('ref'), line_id=line_id)

        reservation.invalidate_recordset(['payment_ids'])
        reservation._compute_amounts()

        return {
            'payment_id': pay.id,
            'ticket_number': pay.ticket_number,
            'state': reservation.state,
            'amount_total': reservation.amount_total,
            'amount_paid': reservation.amount_paid,
            'amount_due': reservation.amount_due,
        }

    # ==================================================================
    # === MÉTODO 'complete' MODIFICADO (REQ 3) ===
    # ==================================================================
    @api.model
    def complete(self, reservation_id):
        resv = self.browse(reservation_id)
        if not resv:
            raise UserError(_('Reserva no encontrada.'))
        resv._compute_amounts()
        if resv.amount_paid + 1e-6 < resv.amount_total:
            raise ValidationError(_('La reserva no está pagada al 100%.'))

        # Create invoice with frozen prices
        if not resv.invoice_id:
            move = self._create_invoice_from_reservation(resv)
            resv.invoice_id = move.id

        # Release holds (custom model state)
        resv.hold_ids.action_release()
        
        # --- MODIFICACIÓN INICIA (REQ 3) ---
        
        # NO cancelar el picking de reserva original (esto devolvería el stock a 'Existencias')
        # self._cancel_reservation_picking(resv) # <-- LÍNEA ORIGINAL ELIMINADA
        
        # En su lugar, crear el picking de ENTREGA FINAL
        # Moverá el stock desde la ubicación 'Apartados' al 'Cliente'
        final_picking = False
        try:
            final_picking = self._create_final_delivery_picking(resv)
            if final_picking:
                resv.final_picking_id = final_picking.id
                _logger.info('Layaway %s: created final delivery %s', resv.name, final_picking.name)
        except Exception as e:
            _logger.error('Layaway %s: failed creating final delivery picking: %s', resv.name, e)
            # Opcional: elevar un UserError si la creación del picking de entrega es crítica
            # raise UserError(_('No se pudo crear el picking de entrega final: %s') % e)
        
        # --- MODIFICACIÓN TERMINA ---

        resv.state = 'invoiced'
        
        return_data = {
            'invoice_id': resv.invoice_id.id if resv.invoice_id else False,
            'invoice_name': resv.invoice_id.name if resv.invoice_id else False,
        }
        if final_picking:
            return_data['picking_id'] = final_picking.id
        
        return return_data

    # ==================================================================
    # === MÉTODO PARA CREAR FACTURA DESDE POS ===
    # ==================================================================
    @api.model
    def create_invoice_from_pos(self, reservation_id):
        """
        Método llamado desde el POS para crear factura cuando el apartado está pagado
        """
        resv = self.browse(reservation_id)
        if not resv:
            raise UserError(_('Reserva no encontrada.'))
        
        resv._compute_amounts()
        
        if resv.amount_paid + 1e-6 < resv.amount_total:
            raise ValidationError(_('La reserva no está pagada al 100%. Saldo pendiente: %.2f') % resv.amount_due)
        
        if resv.state == 'invoiced':
            raise UserError(_('Este apartado ya tiene una factura creada.'))
        
        # Create invoice with frozen prices
        if not resv.invoice_id:
            move = self._create_invoice_from_reservation(resv)
            resv.invoice_id = move.id
        
        # Release holds (custom model state)
        resv.hold_ids.action_release()
        
        # Crear el picking de ENTREGA FINAL
        final_picking = False
        try:
            final_picking = self._create_final_delivery_picking(resv)
            if final_picking:
                resv.final_picking_id = final_picking.id
                _logger.info('Layaway %s: created final delivery %s from POS', resv.name, final_picking.name)
        except Exception as e:
            _logger.error('Layaway %s: failed creating final delivery picking from POS: %s', resv.name, e)
        
        resv.state = 'invoiced'
        
        return {
            'success': True,
            'invoice_id': resv.invoice_id.id if resv.invoice_id else False,
            'invoice_name': resv.invoice_id.name if resv.invoice_id else False,
            'picking_id': final_picking.id if final_picking else False,
            'state': resv.state,
        }

    @api.model
    def create_invoice_from_pos_with_validation(self, reservation_id):
        """
        Método llamado desde el POS para crear factura y enviarla a la DIAN
        Sigue el flujo completo del POS: crear factura -> validar -> enviar a DIAN -> preparar datos para impresión
        """
        resv = self.browse(reservation_id)
        if not resv:
            raise UserError(_('Reserva no encontrada.'))
        
        resv._compute_amounts()
        
        if resv.amount_paid + 1e-6 < resv.amount_total:
            raise ValidationError(_('La reserva no está pagada al 100%. Saldo pendiente: %.2f') % resv.amount_due)
        
        if resv.state == 'invoiced':
            raise UserError(_('Este apartado ya tiene una factura creada.'))
        
        try:
            # Create invoice with frozen prices
            if not resv.invoice_id:
                move = self._create_invoice_from_reservation(resv)
                resv.invoice_id = move.id
            
            # Validar la factura (cambiar de borrador a publicada)
            if resv.invoice_id.state == 'draft':
                resv.invoice_id.action_post()
            
            # Esperar a que se procese la factura electrónica con la DIAN
            # La localización colombiana procesa esto automáticamente al hacer action_post()
            # Refrescar el registro para obtener los datos actualizados de la DIAN
            resv.invoice_id.invalidate_recordset(['l10n_co_edi_cufe_cude_ref', 'l10n_co_dian_state', 'l10n_co_dian_attachment_id'])
            
            # Release holds (custom model state)
            resv.hold_ids.action_release()
            
            # Crear el picking de ENTREGA FINAL
            final_picking = False
            try:
                final_picking = self._create_final_delivery_picking(resv)
                if final_picking:
                    resv.final_picking_id = final_picking.id
                    _logger.info('Layaway %s: created final delivery %s from POS with validation', resv.name, final_picking.name)
            except Exception as e:
                _logger.error('Layaway %s: failed creating final delivery picking from POS: %s', resv.name, e)
            
            resv.state = 'invoiced'
            
            # Preparar datos para impresión en el POS (similar a lo que hace pos.order)
            invoice_data = self._prepare_invoice_data_for_pos(resv)
            
            return {
                'success': True,
                'invoice_id': resv.invoice_id.id if resv.invoice_id else False,
                'invoice_name': resv.invoice_id.name if resv.invoice_id else False,
                'invoice_number': resv.invoice_id.name if resv.invoice_id else False,
                'picking_id': final_picking.id if final_picking else False,
                'state': resv.state,
                'cufe': invoice_data.get('cufe'),
                'qr_code_value': invoice_data.get('qr_code_value'),
                'qr_code_url': invoice_data.get('qr_code_url'),
                'dian_state': invoice_data.get('dian_state'),
                'message': _('Factura creada y validada exitosamente'),
                'invoice_data': invoice_data,  # Datos completos para el recibo
            }
            
        except Exception as e:
            _logger.error('Error creating invoice from POS with validation for reservation %s: %s', resv.name, str(e))
            return {
                'success': False,
                'message': str(e)
            }

    def _prepare_invoice_data_for_pos(self, resv):
        """
        Prepara los datos de la factura para ser usados en el POS
        Similar a _export_for_ui de pos.order
        """
        invoice = resv.invoice_id
        if not invoice:
            return {}
        
        # Obtener el CUFE/CUDE
        cufe = None
        if hasattr(invoice, 'l10n_co_edi_cufe_cude_ref'):
            cufe = invoice.l10n_co_edi_cufe_cude_ref
        elif hasattr(invoice, 'cufe_cude_ref'):
            cufe = invoice.cufe_cude_ref
        
        # Obtener el estado de la DIAN
        dian_state = None
        if hasattr(invoice, 'l10n_co_dian_state'):
            dian_state = invoice.l10n_co_dian_state
        
        # Generar QR Code si está disponible
        qr_code_value = None
        qr_code_url = None
        if hasattr(invoice, 'l10n_co_dian_attachment_id') and invoice.l10n_co_dian_attachment_id:
            try:
                from lxml import etree
                root = etree.fromstring(invoice.l10n_co_dian_attachment_id.raw)
                nsmap = {k: v for k, v in root.nsmap.items() if k}
                qr_code_value = root.findtext(
                    './ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/sts:DianExtensions/sts:QRCode',
                    namespaces=nsmap
                )
                if qr_code_value:
                    qr_code_url = f'/report/barcode/?barcode_type=QR&value={qr_code_value}&width=180&height=180'
            except Exception as e:
                _logger.warning(f"Error generating QR for reservation {resv.name}: {e}")
        
        # Preparar líneas de la factura para el recibo
        invoice_lines = []
        for line in invoice.invoice_line_ids:
            invoice_lines.append({
                'product_name': line.name,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'discount': line.discount,
                'price_subtotal': line.price_subtotal,
                'price_total': line.price_total,
                'tax_ids': [{'name': tax.name, 'amount': tax.amount} for tax in line.tax_ids],
            })
        
        return {
            'invoice_id': invoice.id,
            'invoice_name': invoice.name,
            'invoice_number': invoice.name,
            'cufe': cufe,
            'qr_code_value': qr_code_value,
            'qr_code_url': qr_code_url,
            'dian_state': dian_state,
            'partner_id': invoice.partner_id.id,
            'partner_name': invoice.partner_id.name,
            'partner_vat': invoice.partner_id.vat,
            'partner_street': invoice.partner_id.street,
            'partner_city': invoice.partner_id.city,
            'partner_phone': invoice.partner_id.phone,
            'amount_untaxed': invoice.amount_untaxed,
            'amount_tax': invoice.amount_tax,
            'amount_total': invoice.amount_total,
            'date_invoice': invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else False,
            'invoice_lines': invoice_lines,
            'company_name': invoice.company_id.name,
            'company_vat': invoice.company_id.vat,
            'company_street': invoice.company_id.street,
            'company_phone': invoice.company_id.phone,
            'company_email': invoice.company_id.email,
        }
        
    def action_complete(self):
        self.ensure_one()
        data = self.complete(self.id)
        if data.get('invoice_id'):
            action = self.env.ref('account.action_move_out_invoice_type').read()[0]
            action['domain'] = [('id', '=', data['invoice_id'])]
            return action
        return True

    def action_view_picking(self):
        self.ensure_one()
        # Modificado para mostrar ambos pickings (Reserva y Entrega)
        pickings = self.picking_id | self.final_picking_id
        if not pickings:
             pickings = self.env['stock.picking'].search([('origin', '=', self.name)])

        if len(pickings) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Transferencia'),
                'res_model': 'stock.picking',
                'view_mode': 'form',
                'res_id': pickings.id,
                'target': 'current',
            }
        
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['domain'] = [('id', 'in', pickings.ids)]
        action['name'] = _('Transferencias de Apartado')
        return action

    def action_view_payments(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Abonos'),
            'res_model': 'pos.reservation.payment',
            'view_mode': 'list,form',
            'domain': [('reservation_id', '=', self.id)],
            'context': {'default_reservation_id': self.id},
            'target': 'current',
        }
        return action

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            return False
        # Abrir directamente la factura
        return {
            'type': 'ir.actions.act_window',
            'name': _('Factura'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
            'target': 'current',
        }

    def _default_hold_location(self, reservation):
        # Crear/obtener una ubicación de Apartados debajo del origen (robusto)
        src_loc = self._get_reservation_source_location(reservation)
        hold = self._get_or_create_default_hold_location(src_loc, reservation.company_id)
        return hold.id if hold else False

    def _create_invoice_from_reservation(self, resv):
        Move = self.env['account.move']
        lines_cmd = []
        for l in resv.line_ids:
            vals = {
                'product_id': l.product_id.id,
                'name': l.name or l.product_id.display_name,
                'quantity': l.qty,
                'price_unit': l.price_unit_fixed,
                'discount': l.discount,
                'tax_ids': [(6, 0, l.product_id.taxes_id.filtered(lambda t: t.company_id == resv.company_id).ids)],
            }
            lines_cmd.append((0, 0, vals))
        move = Move.create({
            'move_type': 'out_invoice',
            'partner_id': resv.partner_id.id,
            'invoice_line_ids': lines_cmd,
        })
        move.action_post()

        # Reconcile available credits (payments) against the invoice receivable
        self._reconcile_reservation_credits(resv, move)
        return move

    def _reconcile_reservation_credits(self, resv, invoice_move):
        """
        Intenta conciliar los pagos previos (anticipos) con la factura creada.
        Si no es posible, simplemente registra el intento sin fallar.
        """
        try:
            # Usar account_type en lugar de internal_type (cambio en versiones recientes de Odoo)
            receivable_lines = invoice_move.line_ids.filtered(
                lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
            )
            if not receivable_lines:
                _logger.info('Layaway %s: No hay líneas de cuentas por cobrar en la factura para conciliar', resv.name)
                return
            
            # Buscar créditos (pagos previos) del cliente
            domain = [
                ('partner_id', '=', resv.partner_id.id),
                ('account_id.account_type', '=', 'asset_receivable'),
                ('reconciled', '=', False),
                ('move_id', '!=', invoice_move.id),
                ('move_id.state', '=', 'posted'),  # Solo asientos publicados
                ('balance', '<', 0),  # credits (saldo negativo = a favor del cliente)
            ]
            credits = self.env['account.move.line'].search(domain)
            
            if not credits:
                _logger.info('Layaway %s: No se encontraron créditos previos para conciliar con la factura', resv.name)
                return
            
            _logger.info('Layaway %s: Intentando conciliar %d líneas de crédito con la factura', resv.name, len(credits))
            
            lines_to_reconcile = receivable_lines | credits
            lines_to_reconcile.reconcile()
            
            _logger.info('Layaway %s: Conciliación exitosa', resv.name)
        except Exception as e:
            # Si falla la conciliación, solo registrar el error pero no fallar la creación de la factura
            _logger.warning('Layaway %s: No se pudo conciliar automáticamente los pagos con la factura: %s', resv.name, str(e))
            # La factura ya está creada, el usuario puede conciliar manualmente si es necesario

    def action_cancel(self):
        self.ensure_one()
        if not self.env.user.has_group('pos_reservation_layaway.group_pos_reservation_manager'):
            raise UserError(_('No tiene permisos para cancelar apartados.'))
        self.state = 'cancelled'
        self.hold_ids.action_release()
        # Al cancelar el apartado, SÍ revertimos el movimiento de stock
        self._cancel_reservation_picking(self)

    def _create_payment(self, reservation, amount, journal_id, ref=None, line_id=None):
        """Crea un pago de cliente (account.payment) para registrar el anticipo.
        Integra con realnet_anticipos para usar la cuenta de anticipos del cliente.
        """
        Pay = self.env['pos.reservation.payment']
        # Validaciones básicas de diario/método
        journal = self.env['account.journal'].sudo().browse(journal_id) if journal_id else self.env['account.journal'].sudo().search([
            ('type', 'in', ['cash', 'bank']), ('company_id', '=', reservation.company_id.id)
        ], limit=1)
        if not journal:
            raise UserError(_('Configure al menos un Diario de tipo Caja o Banco para registrar abonos de apartados.'))
        # Método de pago (entrante)
        method_line = journal.inbound_payment_method_line_ids[:1]
        if not method_line:
            # Fallback: buscar cualquier método entrante en el diario
            method_line = journal.payment_method_line_ids.filtered(lambda l: l.payment_type == 'inbound')[:1]
        if not method_line:
            raise UserError(_('El diario %s no tiene un método de pago entrante configurado.') % journal.display_name)

        apay_vals = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': reservation.partner_id.id,
            'amount': amount,
            'currency_id': reservation.currency_id.id,
            'date': fields.Date.context_today(self),
            'journal_id': journal.id,
            'payment_method_line_id': method_line.id,
        }
        # Set a memo/reference field compatible with current Odoo version
        memo = (ref or reservation.name)[:255]
        pay_model = self.env['account.payment']
        if 'payment_reference' in pay_model._fields:
            apay_vals['payment_reference'] = memo
        elif 'ref' in pay_model._fields:
            apay_vals['ref'] = memo
        elif 'narration' in pay_model._fields:
            apay_vals['narration'] = memo
        apay = self.env['account.payment'].sudo().create(apay_vals)
        apay.sudo().action_post()

        payment = Pay.create({
            'reservation_id': reservation.id,
            'line_id': line_id,
            'date': fields.Datetime.now(),
            'amount': amount,
            'journal_id': journal.id,
            'pos_payment_ref': ref or '',
            'state': 'posted',
            'account_payment_id': apay.id,
        })
        return payment

    @api.model
    def cron_mark_expired(self):
        today = fields.Date.context_today(self)
        resv = self.search([('state', 'in', ['reserved', 'draft']), ('expiration_date', '<', today)])
        for r in resv:
            r.state = 'expired'
            r.hold_ids.action_release()
            # Al expirar, también revertimos el movimiento
            self._cancel_reservation_picking(r)

    # ---------------------------
    # Stock reservation helpers
    # ---------------------------

    # ==================================================================
    # === NUEVO MÉTODO AÑADIDO (REQ 3) ===
    # ==================================================================
    def _create_final_delivery_picking(self, reservation):
        """
        Crea el picking de entrega final (Salida).
        Origen: Ubicación de Apartados (Hold)
        Destino: Ubicación de Clientes
        """
        reservation.ensure_one()
        Picking = self.env['stock.picking'].sudo()
        Move = self.env['stock.move'].sudo()

        # 1. Ubicación de Origen (La ubicación de Apartados)
        # La obtenemos del picking de reserva original (transferencia interna)
        hold_location = reservation.picking_id.location_dest_id
        if not hold_location:
            _logger.warning('Layaway %s: No se encontró el picking de reserva original (picking_id) para determinar la ubicación de Apartados.', reservation.name)
            # Fallback por si acaso
            hold_location = self._get_hold_location(reservation)
        
        if not hold_location or hold_location.usage != 'internal':
             _logger.error('Layaway %s: No se puede crear la entrega final. La ubicación de Apartados %s es inválida o no es interna.', reservation.name, hold_location.display_name)
             raise UserError(_('La ubicación de Apartados configurada (%s) no es válida.') % hold_location.display_name)

        # 2. Ubicación de Destino (Clientes)
        customer_location = self.env['stock.location'].search([('usage', '=', 'customer')], limit=1)
        if not customer_location:
             raise UserError(_('No se encontró una ubicación de tipo "Cliente" (usage=customer). Verifique la configuración de Inventario.'))

        # 3. Tipo de Operación (Salida / Delivery Order)
        # Usamos el tipo de operación estándar de Salida del POS
        picking_type = reservation.pos_config_id.picking_type_id
        if not picking_type or picking_type.code != 'outgoing':
             # Fallback: buscar un tipo de salida (outgoing) del almacén del POS
             warehouse = reservation.pos_config_id.picking_type_id.warehouse_id
             if warehouse:
                 picking_type = warehouse.out_type_id
             
        if not picking_type or picking_type.code != 'outgoing':
            # Fallback final: cualquier tipo de salida de la compañía
            picking_type = self.env['stock.picking.type'].search([
                 ('code', '=', 'outgoing'), 
                 ('company_id', '=', reservation.company_id.id)
            ], limit=1)

        if not picking_type:
            raise UserError(_('No se encontró un Tipo de Operación de Salida (Entrega) para el POS o la compañía.'))
        
        # 4. Crear el Picking de Salida
        picking_vals = {
            'picking_type_id': picking_type.id,
            'origin': reservation.name,
            'partner_id': reservation.partner_id.id,
            'location_id': hold_location.id,       # <-- Origen: Apartados
            'location_dest_id': customer_location.id, # <-- Destino: Cliente
            'company_id': reservation.company_id.id,
            'scheduled_date': fields.Datetime.now(),
        }
        picking = Picking.create(picking_vals)

        # 5. Crear los Movimientos de Stock
        moves_created = self.env['stock.move']
        for line in reservation.line_ids:
            if line.product_id.type not in ('product', 'consu') or line.qty <= 0:
                continue
            mv = Move.create({
                'name': _('Layaway Entrega: %s') % (reservation.name,),
                'product_id': line.product_id.id,
                'product_uom': line.product_id.uom_id.id,
                'product_uom_qty': line.qty,
                'picking_id': picking.id,
                'location_id': hold_location.id,
                'location_dest_id': customer_location.id,
                'company_id': reservation.company_id.id,
            })
            moves_created |= mv

        if not moves_created:
            _logger.warning("Layaway %s: El picking de entrega final %s no tiene productos almacenables.", reservation.name, picking.name)
            return picking

        # 6. Confirmar y Validar automáticamente la entrega
        picking.action_confirm()
        picking.action_assign() # Reservar el stock (que debe estar en 'Apartados')

        # Verificar reserva completa (por seguridad, aunque debería estar completo)
        shortages = []
        for mv in picking.move_ids:
            if mv.product_id and mv.product_id.type not in ('product', 'consu'):
                continue
            requested = mv.product_uom_qty or 0.0
            reserved = getattr(mv, 'reserved_availability', 0.0) or sum(ml.reserved_uom_qty for ml in mv.move_line_ids)
            if (reserved + 1e-6) < requested:
                shortages.append((mv.product_id, requested, reserved))

        if shortages:
            details = "\n".join([
                "- %s: solicitado %.2f, reservado %.2f en %s" % (prod.display_name, req, res, hold_location.display_name)
                for (prod, req, res) in shortages
            ])
            _logger.warning('Layaway %s: entrega final con reserva parcial %s\n%s', reservation.name, getattr(picking, 'name', picking.id), details)

        # Validar con cantidades reservadas
        for ml in picking.move_line_ids:
            done_qty = getattr(ml, 'reserved_uom_qty', 0.0) or ml.product_uom_qty
            if done_qty > 0:
                ml.qty_done = done_qty

        try:
            picking.with_context(skip_immediate=True, skip_backorder=True).button_validate()
            _logger.info("Layaway %s: Picking de entrega final %s validado.", reservation.name, picking.name)
        except Exception as e:
            _logger.error('Layaway %s: Falló la auto-validación de la entrega final %s: %s', reservation.name, picking.name, e)
        
        return picking

    # --- Métodos de ayuda (sin cambios) ---

    def _get_hold_location(self, reservation):
        ICP = self.env['ir.config_parameter'].sudo()
        hold_location_id = ICP.get_param('pos_reservation_layaway.hold_location_id')
        hold_location_id = int(hold_location_id) if hold_location_id else False
        if hold_location_id:
            return self.env['stock.location'].browse(hold_location_id)
        # Fallback: pick any internal location different from source
        source = self._get_reservation_source_location(reservation)
        domain = [('usage', '=', 'internal')]
        if reservation.company_id:
            domain.append(('company_id', '=', reservation.company_id.id))
        loc = self.env['stock.location'].search(domain, limit=1)
        # Ensure different from source if possible
        if loc and source and loc.id == source.id:
            alt = self.env['stock.location'].search([('usage', '=', 'internal'), ('id', '!=', source.id)], limit=1)
            if alt:
                loc = alt
        return loc

    def _get_reservation_source_location(self, reservation):
        """Devuelve SIEMPRE una ubicación interna válida para origen.
        Intenta: POS warehouse.lot_stock_id → default_location_src_id si es interna →
        cualquier ubicación interna de la compañía.
        """
        picking_type = reservation.pos_config_id.picking_type_id
        # 1) Almacén principal del POS
        wh = picking_type.warehouse_id if picking_type else False
        if wh and wh.lot_stock_id:
            return wh.lot_stock_id
        # 2) Default del tipo si es interna
        if picking_type and picking_type.default_location_src_id and picking_type.default_location_src_id.usage == 'internal':
            return picking_type.default_location_src_id
        # 3) Cualquier interna de la compañía
        domain = [('usage', '=', 'internal')]
        if reservation.company_id:
            domain.append(('company_id', '=', reservation.company_id.id))
        loc = self.env['stock.location'].search(domain, limit=1)
        return loc

    def _get_location_ancestors(self, location):
        ids = []
        loc = location
        while loc:
            ids.append(loc.id)
            loc = loc.location_id
        return ids

    def _get_warehouse_for_location(self, location, company):
        Warehouse = self.env['stock.warehouse']
        anc_ids = self._get_location_ancestors(location)
        wh = Warehouse.search([('company_id', '=', company.id), ('view_location_id', 'in', anc_ids)], limit=1)
        if not wh:
            wh = Warehouse.search([('company_id', '=', company.id), ('lot_stock_id', 'in', anc_ids)], limit=1)
        return wh

    def _get_or_create_default_hold_location(self, source_location, company):
        Location = self.env['stock.location'].sudo()
        hold = Location.search([
            ('usage', '=', 'internal'),
            ('location_id', '=', source_location.id),
            ('name', 'in', ['Reservas POS', 'Hold POS', 'Apartados POS'])
        ], limit=1)
        if not hold:
            hold = Location.create({
                'name': 'Reservas POS',
                'usage': 'internal',
                'location_id': source_location.id,
                'company_id': company.id if company else False,
            })
            _logger.info('Layaway: created default hold location %s under %s', hold.display_name, source_location.display_name)
        return hold

    def _get_internal_picking_type(self, reservation, warehouse=None):
        PickingType = self.env['stock.picking.type']
        company = reservation.company_id
        if not warehouse and reservation.pos_config_id and reservation.pos_config_id.picking_type_id:
            warehouse = reservation.pos_config_id.picking_type_id.warehouse_id
        domain = [('code', '=', 'internal')]
        if warehouse:
            domain.append(('warehouse_id', '=', warehouse.id))
        elif company:
            domain.append(('company_id', '=', company.id))
        ptype = PickingType.search(domain, limit=1)
        if not ptype:
            # final fallback: any internal picking type
            ptype = PickingType.search([('code', '=', 'internal')], limit=1)
        if not ptype:
            raise UserError(_('No se encontró un tipo de operación interna para crear la reserva de stock.'))
        return ptype

    def _create_reservation_picking(self, reservation):
        reservation.ensure_one()
        Picking = self.env['stock.picking'].sudo()
        Move = self.env['stock.move'].sudo()
        dest = self._get_hold_location(reservation)
        src_init = self._get_reservation_source_location(reservation)

        # Asegurar que ambas ubicaciones sean internas (robusto ante mala config)
        if not src_init or src_init.usage != 'internal':
            # Fallback definitivo: buscar un interno de la compañía
            src_init = self._get_reservation_source_location(reservation)
            if not src_init or src_init.usage != 'internal':
                domain_src = [('usage', '=', 'internal')]
                if reservation.company_id:
                    domain_src.append(('company_id', '=', reservation.company_id.id))
                src_init = self.env['stock.location'].search(domain_src, limit=1)
        if not src_init or src_init.usage != 'internal':
            raise UserError(_("No se encontró una ubicación de origen interna para el POS. Revise la configuración del tipo de operación del POS."))

        if not dest or dest.usage != 'internal':
            dest = self._get_or_create_default_hold_location(src_init, reservation.company_id)
            _logger.warning("Layaway %s: La ubicación de Hold configurada no era interna. Usando fallback %s", reservation.name, getattr(dest, 'display_name', dest.id))

        dest_wh = self._get_warehouse_for_location(dest, reservation.company_id) if dest else False
        ptype = self._get_internal_picking_type(reservation, warehouse=dest_wh)
        src = ptype.default_location_src_id or src_init # Usar la fuente del tipo de operación si existe

        # Pre-chequeo: validar disponibilidad antes de crear el picking
        Quant = self.env['stock.quant']
        shortages_pre = []
        for line in reservation.line_ids:
            if line.product_id.type not in ('product', 'consu') or line.qty <= 0:
                continue
            avail = Quant._get_available_quantity(line.product_id, src)
            if (avail + 1e-6) < line.qty:
                shortages_pre.append((line.product_id, line.qty, avail))

        if shortages_pre:
            details = "\n".join([
                "- %s: solicitado %.2f, máximo apartable %.2f en %s" % (prod.display_name, req, avail, src.display_name)
                for (prod, req, avail) in shortages_pre
            ])
            _logger.warning('Layaway %s: disponibilidad insuficiente en %s (no se bloquea)\n%s', reservation.name, src.display_name, details)

        picking_vals = {
            'picking_type_id': ptype.id,
            'origin': reservation.name,
            'location_id': src.id,
            'location_dest_id': dest.id,
            'company_id': reservation.company_id.id if reservation.company_id else False,
            'scheduled_date': fields.Datetime.now(),
        }
        picking = Picking.create(picking_vals)
        _logger.info('Layaway picking init: type=%s, src=%s, dest=%s', ptype.display_name, src.display_name, dest.display_name)

        # Create stock moves for storable/consumable products only
        moves_created = self.env['stock.move']
        for line in reservation.line_ids:
            if line.product_id.type not in ('product', 'consu'):
                continue
            if line.qty <= 0:
                continue
            mv = Move.create({
                'name': _('Layaway: %s') % (reservation.name,),
                'product_id': line.product_id.id,
                'product_uom': line.product_id.uom_id.id,
                'product_uom_qty': line.qty,
                'picking_id': picking.id,
                'location_id': src.id,
                'location_dest_id': dest.id,
                'company_id': reservation.company_id.id if reservation.company_id else False,
            })
            moves_created |= mv
            _logger.info('Layaway move created: product=%s, qty=%s', line.product_id.display_name, line.qty)

        if not moves_created:
            # Nothing to reserve
            return picking

        # Confirm and reserve quantities
        picking.action_confirm()
        picking.action_assign()
        if not picking.move_line_ids:
            _logger.warning('Layaway %s: no stock reserved for picking %s. Check on-hand in %s.', reservation.name, getattr(picking, 'name', picking.id), src.display_name)

        # Verificar que cada movimiento esté totalmente reservado
        shortages = []
        for mv in picking.move_ids:
            # Validar almacenables y consumibles (no servicios)
            if mv.product_id and mv.product_id.type not in ('product', 'consu'):
                continue
            requested = mv.product_uom_qty or 0.0
            reserved_ml = sum(getattr(ml, 'reserved_uom_qty', getattr(ml, 'product_uom_qty', 0.0)) for ml in mv.move_line_ids)
            reserved_mv = getattr(mv, 'reserved_availability', 0.0)
            reserved = reserved_mv if reserved_mv else reserved_ml
            if (reserved + 1e-6) < requested:
                shortages.append((mv.product_id, requested, reserved))

        if shortages:
            details = "\n".join([
                "- %s: solicitado %.2f, disponible %.2f en %s" % (prod.display_name, req, res, src.display_name)
                for (prod, req, res) in shortages
            ])
            _logger.warning('Layaway %s: picking con reserva parcial %s\n%s', reservation.name, getattr(picking, 'name', picking.id), details)

        # Auto-validate internal transfer
        ICP = self.env['ir.config_parameter'].sudo()
        auto_validate = ICP.get_param('pos_reservation_layaway.auto_validate_picking', 'True')
        if str(auto_validate).lower() in ('1', 'true', 'yes') and picking.move_line_ids:
            # Solo validar con cantidades efectivamente reservadas
            for ml in picking.move_line_ids:
                done_qty = getattr(ml, 'reserved_uom_qty', 0.0)
                if done_qty > 0:
                    ml.qty_done = done_qty
            try:
                picking.with_context(skip_immediate=True, skip_backorder=True).button_validate()
            except Exception as e:
                _logger.warning('Layaway %s: button_validate failed (%s), trying _action_done()', reservation.name, e)
                try:
                    picking.move_ids._action_done()
                except Exception as e2:
                    _logger.error('Layaway %s: _action_done failed: %s', reservation.name, e2)
        return picking

    def _cancel_reservation_picking(self, reservation):
        """ Cancela Y REVVIERTE el picking de reserva inicial. """
        picking = reservation.picking_id.sudo()
        if not picking or picking.state == 'cancel':
            return
        
        # Si el picking ya se completó (movió a Apartados), debemos crear un picking de retorno
        if picking.state == 'done':
            # Creamos un picking de retorno de Apartados -> Existencias
            Picking = self.env['stock.picking'].sudo()
            Move = self.env['stock.move'].sudo()

            return_picking = Picking.create({
                'picking_type_id': picking.picking_type_id.id,
                'origin': _('Retorno de %s') % reservation.name,
                'partner_id': reservation.partner_id.id,
                'location_id': picking.location_dest_id.id, # Origen: Apartados
                'location_dest_id': picking.location_id.id, # Destino: Existencias
                'company_id': reservation.company_id.id,
                'scheduled_date': fields.Datetime.now(),
            })

            for move in picking.move_ids.filtered(lambda m: m.state == 'done'):
                Move.create({
                    'name': _('Retorno: %s') % (move.name,),
                    'product_id': move.product_id.id,
                    'product_uom': move.product_uom.id,
                    'product_uom_qty': move.quantity_done,
                    'picking_id': return_picking.id,
                    'location_id': move.location_dest_id.id,
                    'location_dest_id': move.location_id.id,
                    'company_id': reservation.company_id.id,
                })
            
            if return_picking.move_ids:
                return_picking.action_confirm()
                return_picking.action_assign()
                # Auto-validar el retorno
                for ml in return_picking.move_line_ids:
                    ml.qty_done = ml.product_uom_qty
                return_picking.button_validate()
            
            # Cancelamos el original solo como referencia
            picking.action_cancel()

        # Si el picking no estaba 'done', solo lo cancelamos
        elif picking.state not in ('done', 'cancel'):
            try:
                picking.action_unreserve()
            except Exception:
                pass
            try:
                picking.action_cancel()
            except Exception:
                pass

class PosReservationLine(models.Model):
    _name = 'pos.reservation.line'
    _description = 'POS Reservation Line'
    _order = 'id'

    reservation_id = fields.Many2one('pos.reservation', string='Reserva', required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='Producto', required=True)
    name = fields.Char('Descripción')
    qty = fields.Float('Cantidad', required=True, default=1.0)
    price_unit_fixed = fields.Monetary('Precio Fijo', required=True, default=0.0, currency_field='currency_id')
    discount = fields.Float('Descuento (%)', default=0.0)
    price_subtotal = fields.Monetary('Subtotal', compute='_compute_subtotal', store=True, currency_field='currency_id')
    amount_paid_line = fields.Monetary('Pagado Línea', compute='_compute_paid_line', store=True, currency_field='currency_id')
    amount_due_line = fields.Monetary('Saldo Línea', compute='_compute_paid_line', store=True, currency_field='currency_id')
    state = fields.Selection([('reserved', 'Reservado'), ('paid', 'Pagado'), ('cancelled', 'Cancelado')], default='reserved')
    stock_reservation_id = fields.Many2one('stock.reservation.hold', string='Hold')
    currency_id = fields.Many2one(related='reservation_id.currency_id', store=True, readonly=True)

    @api.depends('qty', 'price_unit_fixed', 'discount')
    def _compute_subtotal(self):
        for l in self:
            l.price_subtotal = l.qty * l.price_unit_fixed * (1 - (l.discount or 0.0) / 100.0)

    @api.depends('reservation_id.payment_ids.state', 'reservation_id.payment_ids.amount')
    def _compute_paid_line(self):
        for l in self:
            paid = sum(l.reservation_id.payment_ids.filtered(lambda p: p.state == 'posted' and p.line_id.id == l.id).mapped('amount'))
            l.amount_paid_line = paid
            l.amount_due_line = max(l.price_subtotal - paid, 0.0)
            if l.amount_due_line <= 1e-6 and l.price_subtotal > 0:
                l.state = 'paid'


class PosReservationPayment(models.Model):
    _name = 'pos.reservation.payment'
    _description = 'POS Reservation Payment'
    _order = 'id desc'

    reservation_id = fields.Many2one('pos.reservation', string='Reserva', required=True, ondelete='cascade', index=True)
    line_id = fields.Many2one('pos.reservation.line', string='Línea (opcional)')
    date = fields.Datetime('Fecha', default=fields.Datetime.now)
    amount = fields.Monetary('Monto', required=True)
    journal_id = fields.Many2one('account.journal', string='Método de Pago')
    pos_payment_ref = fields.Char('Referencia Pago POS')
    state = fields.Selection([('posted', 'Publicado'), ('cancelled', 'Cancelado')], default='posted', required=True)
    ticket_number = fields.Char('No. Ticket', default=lambda self: self.env['ir.sequence'].next_by_code('pos.reservation.payment') or '/')
    currency_id = fields.Many2one(related='reservation_id.currency_id', store=True, readonly=True)
    account_payment_id = fields.Many2one('account.payment', string='Pago (contable)', readonly=True, copy=False)
