from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class RegisterPaymentWizard(models.TransientModel):
    """Details for a payment for parking"""
    _name = 'register.payment.wizard'
    _description = 'Register Parking Payment'

    partner_id = fields.Many2one('res.partner',
                                 string='Partner',
                                 help='Name of partner to register the payment')
    parking_duration = fields.Float(string='Duration',
                                    help='Duration of the parking vehicle')
    amount = fields.Float(string='Amount',
                          help='Amount of the parking vehicle')
    ref = fields.Char(string='Reference',
                      help='Reference to the parking ticket')
    date = fields.Date(string='Date', default=fields.Date.context_today,
                       help='Date when payment was made')
    received_amount = fields.Float(string='Monto Recibido',
                                   help='Monto recibido del cliente',
                                   required=True)
    change_amount = fields.Float(string='Cambio a Devolver',
                                 compute='_compute_change_amount',
                                 readonly=True,
                                 help='Monto a devolver al cliente')

    def _compute_change_amount(self):
        for rec in self:
            amount = rec.amount or 0.0
            received = rec.received_amount or 0.0
            change = received - amount
            rec.change_amount = change if change > 0.0 else 0.0

    def _validate_received_amount(self, invoice_currency):
        received = self.received_amount or 0.0
        total = self.amount or 0.0
        if float_compare(received, total, precision_rounding=invoice_currency.rounding) < 0:
            raise ValidationError(_('El monto recibido es insuficiente para cubrir el total.'))

    @api.onchange('received_amount', 'amount')
    def _onchange_received_amount(self):
        for rec in self:
            amount = rec.amount or 0.0
            received = rec.received_amount or 0.0
            change = received - amount
            rec.change_amount = change if change > 0.0 else 0.0

    def parking_payment(self):
        """Returns the amount of the parking ticket for the customer."""
        import logging
        _logger = logging.getLogger(__name__)
        
        active_id = self._context.get('active_id')
        active_record = self.env['parking.entry'].browse(active_id)
        
        _logger.info(f"[PARKING PAYMENT] Iniciando proceso de pago para parking entry {active_record.id}")
        
        # Crear factura si no existe
        if not active_record.invoice_id:
            try:
                invoice = active_record._create_invoice()
                _logger.info(f"[PARKING PAYMENT] Factura creada: {invoice.id}")
            except UserError as e:
                _logger.error(f"[PARKING PAYMENT] Error creando factura: {str(e)}")
                raise UserError(str(e))
        else:
            invoice = active_record.invoice_id
            _logger.info(f"[PARKING PAYMENT] Usando factura existente: {invoice.id}")
        
        # Verificar que la factura esté publicada
        if invoice.state == 'draft':
            invoice.action_post()
            _logger.info(f"[PARKING PAYMENT] Factura publicada, estado: {invoice.state}")
        
        # Crear el pago usando el wizard estándar de Odoo pero programáticamente
        # Política: sin pagos parciales. Validar y forzar pago por el total pendiente.
        residual = invoice.amount_residual
        currency = invoice.currency_id
        if float_compare(residual, 0.0, precision_rounding=currency.rounding) <= 0:
            raise ValidationError(_('La factura ya está saldada. No se pueden registrar pagos.'))
        if float_compare(self.amount or 0.0, residual, precision_rounding=currency.rounding) != 0:
            raise ValidationError(_('No se permiten pagos parciales. Debe pagar el saldo total.'))

        # Validar monto recibido
        self._validate_received_amount(currency)

        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=[invoice.id]
        ).create({
            'amount': residual,
            'payment_date': self.date,
            'communication': self.ref or invoice.name,
        })
        
        _logger.info(f"[PARKING PAYMENT] Payment register creado con monto: {self.amount}")
        
        # Crear y confirmar el pago
        action = payment_register.action_create_payments()
        _logger.info(f"[PARKING PAYMENT] Action create payments resultado: {action}")
        
        # Buscar el pago creado más reciente
        payment = None
        if action and isinstance(action, dict) and 'res_id' in action:
            payment = self.env['account.payment'].browse(action['res_id'])
            _logger.info(f"[PARKING PAYMENT] Pago encontrado por res_id: {payment.id}, estado: {payment.state}")
        
        # Si no encontramos el pago por res_id, busquemos el más reciente
        if not payment:
            payment = self.env['account.payment'].search([
                ('partner_id', '=', self.partner_id.id),
                ('amount', '=', self.amount),
            ], limit=1, order='create_date desc')
            _logger.info(f"[PARKING PAYMENT] Pago encontrado por búsqueda: {payment.id if payment else 'None'}")
        
        if payment:
            _logger.info(f"[PARKING PAYMENT] Pago encontrado: {payment.id}, estado inicial: {payment.state}")
            
            # Si el pago está en draft o in_process, validarlo
            if payment.state in ['draft', 'in_process']:
                try:
                    # Para pagos en estado in_process, usar action_validate en lugar de action_post
                    if payment.state == 'in_process':
                        payment.action_validate()
                    else:
                        payment.action_post()
                    _logger.info(f"[PARKING PAYMENT] Pago validado, nuevo estado: {payment.state}")
                except Exception as e:
                    _logger.error(f"[PARKING PAYMENT] Error validando pago: {str(e)}")
                    raise UserError(f"Error validando el pago: {str(e)}")
            
            # Asociar el pago al parking entry
            active_record.payment_id = payment.id
            _logger.info(f"[PARKING PAYMENT] Pago asociado al parking entry")
            
            # Refrescar el estado de la factura después de validar el pago
            invoice.invalidate_recordset(['payment_state'])
            invoice._compute_amount()
            _logger.info(f"[PARKING PAYMENT] Estado de pago de la factura después de validar: {invoice.payment_state}")
            
            # Verificar si la factura está pagada y actualizar el estado
            if invoice.payment_state in ['paid', 'in_payment']:
                active_record.update_payment_status()
                _logger.info(f"[PARKING PAYMENT] Estado del parking entry actualizado")
            else:
                _logger.warning(f"[PARKING PAYMENT] Factura no marcada como pagada, estado: {invoice.payment_state}")
                # Intentar forzar la conciliación si es necesario
                try:
                    # Buscar líneas de movimiento no conciliadas del pago y la factura
                    payment_lines = payment.move_id.line_ids.filtered(lambda l: l.account_id.account_type in ['asset_receivable', 'liability_payable'] and not l.reconciled)
                    invoice_lines = invoice.line_ids.filtered(lambda l: l.account_id.account_type in ['asset_receivable', 'liability_payable'] and not l.reconciled)
                    
                    if payment_lines and invoice_lines:
                        _logger.info(f"[PARKING PAYMENT] Intentando conciliar líneas manualmente")
                        (payment_lines + invoice_lines).reconcile()
                        
                        # Refrescar estado después de conciliación
                        invoice.invalidate_recordset(['payment_state'])
                        invoice._compute_amount()
                        _logger.info(f"[PARKING PAYMENT] Estado después de conciliación manual: {invoice.payment_state}")
                        
                        if invoice.payment_state == 'paid':
                            active_record.update_payment_status()
                            _logger.info(f"[PARKING PAYMENT] Estado del parking entry actualizado después de conciliación")
                except Exception as e:
                    _logger.warning(f"[PARKING PAYMENT] Error en conciliación manual: {str(e)}")
                
                # Si aún no está pagada, programar verificación
                if invoice.payment_state != 'paid':
                    self.env.cr.commit()
                    self.env['parking.entry']._update_parking_entries_payment_status()
        else:
            _logger.error(f"[PARKING PAYMENT] No se pudo encontrar el pago creado")
            raise UserError("No se pudo crear o encontrar el pago. Por favor, intente nuevamente.")
        
        # Cerrar el popup y permanecer en el módulo (refresco manejado por JS)
        return {
            'type': 'ir.actions.act_window_close',
        }
