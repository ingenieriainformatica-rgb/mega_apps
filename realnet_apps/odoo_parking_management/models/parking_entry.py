import datetime
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ParkingEntry(models.Model):
    """Details about the Parking"""
    _name = 'parking.entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Public Park Entry'

    name = fields.Char(string='Reference', readonly=True,
                       default=lambda self: _('New'),
                       help='Field for the sequence of parking entries')
    partner_id = fields.Many2one('res.partner', string='Contact',
                                 tracking=True, 
                                 default=lambda self: self._get_default_partner(),
                                 help='Field for customer')
    mobile = fields.Char(related='partner_id.phone', string='Mobile',
                         store=True, readonly=False,
                         help='Mobile number of customer')
    email = fields.Char(related='partner_id.email', string='Email',
                        store=True, readonly=False,
                        help='E-mail of customer')
    check_in = fields.Datetime(string='Check In', readonly=True,
                               tracking=True, help='Check In time of the '
                                                   'vehicle for parking')
    vehicle_id = fields.Many2one('vehicle.details', string='Vehicle',
                                 tracking=True, required=False,
                                 ondelete='set null',
                                 help='Vehicle of Customer')
    vehicle_number = fields.Char(related='vehicle_id.number_plate',
                                 string='Vehicle Number', store=True,
                                 readonly=False, tracking=True,
                                 help='Vehicle number of customer')
    slot_type_id = fields.Many2one('slot.type', string='Slot Type',
                                   tracking=True, required=True,
                                   help='Slot type fr the vehicle')
    slot_id = fields.Many2one('slot.details', string='Slot',
                              tracking=True,
                              required=False,
                              help='Slot assigned for vehicle of Customer')
    user_id = fields.Many2one('res.users', string='Created By',
                              default=lambda self: self.env.user,
                              tracking=True,
                              help='Field for user that entries are created')
    created_date = fields.Datetime(string='Created Datetime',
                                   default=lambda self: fields.Datetime.now(),
                                   tracking=True,
                                   help='Date which entry was created')
    check_out = fields.Datetime(string='Check Out', readonly=True,
                                tracking=True, help='Check Out time of vehicle')
    duration = fields.Float(string='Duration', compute='_compute_duration',
                            store=True, help='Time spent by the vehicles')
    customer_type = fields.Selection(
        [('private', 'Private'), ('public', 'Public')],
        string='Type', default='public',
        tracking=True, required=True,
        help='Type of the customer (deprecated: always public)')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 help='Name of the company')
    site_id = fields.Many2one(
        'parking.site',
        string='Parking Site',
        required=True,
        tracking=True,
        index=True,
        help='Parking site where this entry belongs'
    )
    # Helper boolean to drive v17+ view conditional required
    site_requires_slot = fields.Boolean(
        string='Site Requires Slot',
        related='site_id.slot_required',
        help='True when the selected site requires assigning a slot',
        store=False,
        readonly=True,
    )
    location_id = fields.Many2one('location.details',
                                  string='Location',
                                  tracking=True, required=True,
                                  help='Name of the location')
    state = fields.Selection([('draft', 'Draft'),
                              ('check_in', 'Check In'),
                              ('check_out', ' Check Out'),
                              ('payment', 'Payment')],
                             string='Status', default='draft', tracking=True,
                             help='Status of the vehicle', copy=False)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related='company_id.currency_id',
                                  help='Currency used by the company')
    parking_cost = fields.Monetary(string='Parking Cost', tracking=True,
                                   help='Cost for the parking.')
    check_in_bool = fields.Boolean(string='Check In Bool',
                                   default=False,
                                   copy=False,
                                   help='Check if checked in.')
    check_out_bool = fields.Boolean(string='Check Out Bool',
                                    default=False,
                                    copy=False,
                                    help='Check if checked out.')
    paid_bool = fields.Boolean(string='Paid Bool',
                               default=False,
                               copy=False,
                               help='Check if paid.')
    # Convenio / Referencia: Con Sello
    with_stamp = fields.Boolean(
        string='Con Sello',
        default=False,
        help='Aplicar convenio de â€œCon Selloâ€ al calcular el cobro de salida.'
    )
    reference_id = fields.Many2one(
        'parking.reference',
        string='Referencia',
        help='Convenio aplicado cuando se marca â€œCon Selloâ€.'
    )
    # Nuevos campos para facturaciÃ³n
    product_id = fields.Many2one('product.product', string='Service Product',
                                 help='Product service assigned based on slot type')
    invoice_id = fields.Many2one('account.move', string='Invoice',
                                 help='Generated invoice for parking service')
    payment_id = fields.Many2one('account.payment', string='Payment',
                                 help='Payment record for parking service')
    invoice_payment_state = fields.Selection(related='invoice_id.payment_state', 
                                           string='Invoice Payment Status', 
                                           readonly=True)
    # Campo computed para actualizar estado automÃ¡ticamente
    auto_payment_update = fields.Boolean(string='Auto Payment Update', 
                                       compute='_compute_payment_status',
                                       store=False)
    
    # Monthly contract fields
    is_monthly = fields.Boolean(
        string='Is Monthly',
        compute='_compute_is_monthly',
        store=True,
        help='True if this entry belongs to a monthly contract'
    )
    monthly_contract_id = fields.Many2one(
        'parking.monthly.contract',
        string='Monthly Contract',
        help='Monthly contract for this entry'
    )
    monthly_invoice_id = fields.Many2one(
        'account.move',
        string='Monthly Invoice',
        help='Monthly invoice that includes this entry'
    )
    monthly_period = fields.Char(
        string='Monthly Period',
        help='Monthly period in YYYY-MM format'
    )
    receipt_sequence = fields.Char(
        string='Receipt Sequence',
        help='Parking receipt sequence (PARKING/xxxxx)'
    )

    @api.constrains('customer_type')
    def _check_customer_type_public_only(self):
        """Constraint to ensure customer_type is always 'public'"""
        for rec in self:
            if rec.customer_type != 'public':
                # Log warning for deprecated usage
                _logger.warning(f"Deprecated: customer_type='{rec.customer_type}' detected in record {rec.name}. It will be forced to 'public'.")
                raise ValidationError(_("Only 'public' is allowed for customer_type. Private parking is deprecated."))

    @api.constrains('site_id')
    def _check_site_access(self):
        """Validate that user has access to the selected site"""
        for rec in self:
            if rec.site_id:
                user = self.env.user
                # Skip validation for admins
                if user.has_group('odoo_parking_management.group_parking_admin'):
                    continue
                # Check if user has access to this site
                if rec.site_id not in user.allowed_parking_site_ids:
                    raise ValidationError(_(
                        'You do not have access to site "%s". Please contact your administrator.'
                    ) % rec.site_id.name)

    @api.constrains('slot_id', 'slot_type_id', 'site_id')
    def _check_slot_availability_and_type(self):
        """Validate that selected slot is available and matches the slot type"""
        for rec in self:
            if rec.slot_id and rec.slot_type_id:
                # Verificar que el tipo de slot coincida exactamente
                if rec.slot_id.slot_type_id != rec.slot_type_id:
                    raise ValidationError(_(
                        'The selected slot "%s" is of type "%s" but you selected slot type "%s". '
                        'Please select a slot that matches the slot type exactly.'
                    ) % (rec.slot_id.name, rec.slot_id.slot_type_id.name, rec.slot_type_id.name))
                
                # Verificar que el slot estÃ© disponible (no tenga una entrada activa)
                if rec.slot_id.current_parking_entry_id and rec.slot_id.current_parking_entry_id != rec:
                    raise ValidationError(_(
                        'The selected slot "%s" is currently occupied by parking entry "%s". '
                        'Please select an available slot.'
                    ) % (rec.slot_id.name, rec.slot_id.current_parking_entry_id.name))
                
                # Verificar que el slot no estÃ© marcado como no disponible
                if not rec.slot_id.is_available:
                    raise ValidationError(_(
                        'The selected slot "%s" is not available. Please select an available slot.'
                    ) % rec.slot_id.name)
            
            # Verificar que el slot pertenezca a la misma sede
            if rec.slot_id and rec.site_id:
                if rec.slot_id.site_id != rec.site_id:
                    raise ValidationError(_(
                        'The selected slot "%s" belongs to site "%s" but the parking entry is for site "%s". '
                        'Please select a slot from the same site.'
                    ) % (rec.slot_id.name, rec.slot_id.site_id.name, rec.site_id.name))

    @api.constrains('site_id', 'slot_id')
    def _check_slot_required_by_site(self):
        """Enforce slot assignment only when the site requires it"""
        for rec in self:
            if rec.site_id and rec.site_id.slot_required and not rec.slot_id:
                raise ValidationError(_(
                    'This site requires assigning a parking slot. Please select a slot.'
                ))

    @api.model
    def default_get(self, fields_list):
        """Set default site_id, location_id and partner_id based on user configuration"""
        defaults = super().default_get(fields_list)
        
        # Set default partner_id if not already set
        if 'partner_id' in fields_list and not defaults.get('partner_id'):
            defaults['partner_id'] = self._get_default_partner()
        
        # Set default site_id if not already set
        if 'site_id' in fields_list and not defaults.get('site_id'):
            default_site = self.env.user.get_default_parking_site()
            if default_site:
                defaults['site_id'] = default_site.id
                
                # Also set default location_id based on the site's city
                if 'location_id' in fields_list and not defaults.get('location_id'):
                    locations = self.env['location.details'].search([
                        ('city', '=', default_site.city)
                    ], limit=1)
                    if locations:
                        defaults['location_id'] = locations[0].id
                    else:
                        _logger.warning(f"No location found for city '{default_site.city}' in default site '{default_site.name}'")
        
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        """Method for generating the sequence and validating site access"""
        # Process site_id for each record
        for vals in vals_list:
            # Set default site_id if not provided
            if not vals.get('site_id'):
                default_site = self.env.user.get_default_parking_site()
                if default_site:
                    vals['site_id'] = default_site.id
                else:
                    raise ValidationError(_(
                        'No default parking site configured. Please contact your administrator.'
                    ))
            
            # Set location_id based on site's city if not provided
            if not vals.get('location_id') and vals.get('site_id'):
                site = self.env['parking.site'].browse(vals['site_id'])
                if site.city:
                    locations = self.env['location.details'].search([
                        ('city', '=', site.city)
                    ], limit=1)
                    if locations:
                        vals['location_id'] = locations[0].id
                    else:
                        _logger.warning(f"No location found for city '{site.city}' in site '{site.name}'")
            
            # Validate site access for non-admin users
            if not self.env.user.has_group('odoo_parking_management.group_parking_admin'):
                site_id = vals.get('site_id')
                if site_id not in self.env.user.allowed_parking_site_ids.ids:
                    site_name = self.env['parking.site'].browse(site_id).name
                    raise ValidationError(_(
                        'You do not have access to create entries for site "%s".'
                    ) % site_name)
        
        res = super(ParkingEntry, self).create(vals_list)
        for record in res:
            # Assign sequence
            if record.customer_type == "private":
                record.name = self.env['ir.sequence'].next_by_code(
                    'private.parking.entry')
            if record.customer_type == 'public':
                record.name = self.env['ir.sequence'].next_by_code(
                    'public.parking.entry')
            
            # Store receipt sequence for monthly tracking
            record.receipt_sequence = record.name
            
            # Update slot availability after creation
            record._update_slot_availability()
            
            # Handle monthly contract assignment
            if record.is_monthly and record.monthly_contract_id:
                # This will be handled by the monthly aggregation service
                # when the entry is checked out
                pass
            
        return res

    @api.depends('check_out')
    def _compute_duration(self):
        """Method for computing the duration of checking in and checking out
        of vehicles"""
        for rec in self:
            rec.duration = False
            if rec.check_out:
                entry = datetime.datetime.strptime(str(rec.check_in),
                                                   "%Y-%m-%d %H:%M:%S")
                out = datetime.datetime.strptime(str(rec.check_out),
                                                 "%Y-%m-%d %H:%M:%S")
                dur_dif = out - entry
                rec.duration = dur_dif.total_seconds() / 3600.0
                
                # Actualizar el costo automÃ¡ticamente
                if rec.product_id:
                    base_price = rec.product_id.list_price
                    rec.parking_cost = base_price * max(1, rec.duration)

    @api.onchange('slot_type_id')
    def onchange_slot_type_id(self):
        """Method for changing the slot type and assigning the appropriate product"""
        # Limpiar el slot_id cuando cambia el tipo de slot
        self.slot_id = False
        
        # Crear dominio base con tipo de slot y disponibilidad
        domain = []
        
        if self.slot_type_id:
            # Solo mostrar slots que:
            # 1. Tengan exactamente el mismo tipo de slot
            # 2. EstÃ©n disponibles (current_parking_entry_id vacÃ­o)
            # 3. TambiÃ©n verificar que is_available sea True como filtro adicional
            # 4. Pertenezcan a la misma sede (si hay sede seleccionada)
            domain = [
                ('slot_type_id', '=', self.slot_type_id.id),
                ('current_parking_entry_id', '=', False),
                ('is_available', '=', True)
            ]
            
            # Filtrar por sede si estÃ¡ seleccionada
            if self.site_id:
                domain.append(('site_id', '=', self.site_id.id))
            
            # Asignar automÃ¡ticamente el producto basado en el tipo de slot
            self.product_id = self._get_parking_product(self.slot_type_id.vehicle_type)
        
        return {'domain': {'slot_id': domain}}

    @api.onchange('site_id')
    def _onchange_site_id(self):
        """Auto-set location_id based on site's city and update slot_id domain"""
        # Limpiar slot_id cuando cambia la sede
        self.slot_id = False
        
        domain = {'location_id': [], 'slot_id': []}
        
        if self.site_id:
            # Find location for this city
            locations = self.env['location.details'].search([
                ('city', '=', self.site_id.city)
            ])
            
            if locations:
                self.location_id = locations[0]
            else:
                self.location_id = False
            
            # Set location domain
            domain['location_id'] = [('city', '=', self.site_id.city)]
            
            # Set slot domain based on site and slot_type if selected
            if self.slot_type_id:
                domain['slot_id'] = [
                    ('slot_type_id', '=', self.slot_type_id.id),
                    ('current_parking_entry_id', '=', False),
                    ('is_available', '=', True),
                    ('site_id', '=', self.site_id.id)
                ]
            else:
                # Si no hay slot_type seleccionado, mostrar solo slots de esta sede
                domain['slot_id'] = [('site_id', '=', self.site_id.id)]
                
        else:
            # Clear location if no site selected
            self.location_id = False
            
        # Re-evaluar mapeo de placa autorizada al cambiar la sede
        res = {'domain': domain}
        auth_res = self._apply_authorized_partner_from_plate()
        if isinstance(auth_res, dict):
            res.update(auth_res)
        return res

    def action_check_in(self):
        """Method for checking in"""
        self = self.with_context(allow_immutable=True)
        # Bloqueo por Vehículos Sospechosos: si alguna alerta indica bloquear,
        # no permitir registrar la entrada.
        try:
            alerts = self._find_suspicious_alerts()
        except Exception:
            alerts = self.env['parking.suspicious.vehicle']
        if alerts and alerts.filtered(lambda a: not a.print_ticket):
            reasons = '\n- ' + '\n- '.join([a.reason or '' for a in alerts.filtered(lambda a: not a.print_ticket)])
            raise ValidationError(_(
                'Vehículo sospechoso detectado para la placa %s.\n'
                'No se permite registrar la entrada en esta sede.\nMotivos:%s'
            ) % (self.vehicle_number or '-', reasons))
        # Antes de confirmar el ingreso, validar Personal Autorizado y cupos
        self._enforce_authorized_quota_before_checkin()
        # Continuar con el check-in
        self.state = 'check_in'
        self.check_in_bool = True
        self.check_out_bool = False
        self.check_in = fields.Datetime.now()
        
        # Asegurar que se asigne el producto correcto en check-in
        if not self.product_id and self.slot_type_id:
            self.product_id = self._get_parking_product(self.slot_type_id.vehicle_type)
        
        # Update slot availability
        self._update_slot_availability()

    def action_check_out(self):
        """Method for checking out"""
        self = self.with_context(allow_immutable=True)
        self.state = 'check_out'
        self.check_out_bool = True
        self.check_in_bool = False
        self.check_out = fields.Datetime.now()
        
        # Calcular el costo basado en el producto y la duraciÃ³n
        if self.product_id and self.duration > 0:
            # Usar el precio del producto como base
            base_price = self.product_id.list_price
            # Calcular costo total basado en duraciÃ³n (precio por hora)
            # Cobro por hora sin prorrateo (redondeo hacia arriba) para ordinarios
            from math import ceil
            try:
                entry_dt = fields.Datetime.from_string(self.check_in)
                out_dt = fields.Datetime.from_string(self.check_out)
                total_minutes = int(((out_dt - entry_dt).total_seconds() + 59) // 60)
            except Exception:
                total_minutes = int(round(self.duration * 60))
            if not self.with_stamp:
                hours_to_charge = max(1, ceil(total_minutes / 60.0))
                self.parking_cost = base_price * hours_to_charge
            else:
                self.parking_cost = base_price * max(1, self.duration)
        
        # Update slot availability
        self._update_slot_availability()
        
        # Prepaid authorized personnel: skip any invoicing/aggregation
        if self.is_monthly and self.monthly_contract_id:
            return
        else:
            # Para clientes NO mensuales, abrir automÃ¡ticamente el wizard de pago
            return self.action_register_payment_improved()

    @api.onchange('with_stamp', 'site_id')
    def _onchange_with_stamp_set_default_reference(self):
        if self.with_stamp and not self.reference_id:
            domain = [('active', '=', True), ('company_id', '=', self.company_id.id)]
            if self.site_id:
                domain = ['|', ('site_ids', '=', False), ('site_ids', 'in', self.site_id.id)] + domain
            # Priorizar is_default
            ref = self.env['parking.reference'].search(domain + [('is_default', '=', True)], limit=1)
            if not ref:
                ref = self.env['parking.reference'].search(domain + [('name', 'ilike', 'sello')], limit=1)
            self.reference_id = ref

    def action_register_payment(self):
        """Method for viewing the wizard for register payment"""
        # Si existe factura, usar el saldo pendiente (con IVA), sino usar parking_cost
        amount_to_pay = self.invoice_id.amount_residual if self.invoice_id else self.parking_cost
        
        view_id = self.env.ref('odoo_parking_management'
                               '.register_payment_wizard_view_form').id
        return {
            'name': 'Register Payment',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'register.payment.wizard',
            'views': [(view_id, 'form')],
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_parking_duration': self.duration,
                'default_amount': amount_to_pay,  # Ahora incluye el IVA si hay factura
                'default_ref': self.name
            },
            'target': 'new',
        }

    def _create_invoice(self):
        """Crear factura de cliente para el servicio de parqueo"""
        if not self.partner_id:
            raise UserError(_('Customer is required to create an invoice.'))

        if not self.product_id:
            raise UserError(_('Service product is not assigned.'))

        if self.invoice_id:
            raise UserError(_('Invoice already exists for this parking entry.'))

        if self.duration <= 0:
            raise UserError(_('Duration must be greater than 0 to create an invoice.'))

        # Journal
        journal = self.env['account.journal'].search([
            ('name', '=', 'Facturas de parqueadero'),
            ('type', '=', 'sale'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        if not journal:
            journal = self.env['account.journal'].search([
                ('type', '=', 'sale'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
        if not journal:
            raise UserError(_('No customer invoice journal found. Please create "Facturas de parqueadero" journal or any Sale journal.'))

        # Analytic distribution by site
        analytic_distribution = {}
        if self.site_id and self.site_id.analytic_account_id:
            analytic_distribution = {str(self.site_id.analytic_account_id.id): 100.0}

        invoice_lines = []

        if self.with_stamp:
            # Prefer parametrized reference if present
            if self.reference_id:
                lines, cost = self.reference_id.compute_invoice_lines(self, analytic_distribution)
                if not lines:
                    self.state = 'payment'
                    self.paid_bool = True
                    self.parking_cost = 0.0
                    return False
                invoice_lines.extend(lines)
                self.parking_cost = cost
            else:
                veh = (self.slot_type_id.vehicle_type or '').strip().lower()

                def _incl_to_excl(product, amount_incl):
                    taxes = product.taxes_id.filtered(lambda t: t.company_id == self.company_id)
                    rate = sum(t.amount for t in taxes if t.amount_type == 'percent') / 100.0 if taxes else 0.0
                    return round(amount_incl / (1.0 + rate), 2)

                # Minutes actually parked rounded up
                try:
                    entry_dt = fields.Datetime.from_string(self.check_in)
                    out_dt = fields.Datetime.from_string(self.check_out)
                    total_minutes = int(((out_dt - entry_dt).total_seconds() + 59) // 60)
                except Exception:
                    total_minutes = int(round(self.duration * 60))

                if 'moto' in veh:
                    # 0-30 minutes free; from 31 on, hourly at Moto tariff
                    if total_minutes <= 30:
                        self.parking_cost = 0.0
                        self.state = 'payment'
                        self.paid_bool = True
                        return False
                    from math import ceil
                    hours_to_charge = ceil((total_minutes - 30) / 60.0)
                    moto_unit_excl = self.product_id.list_price
                    line_vals = {
                        'product_id': self.product_id.id,
                        'name': f'{self.product_id.name} - {self.name} - {self.site_id.name} (Con Sello, {hours_to_charge} hora(s) desde min 31)',
                        'quantity': hours_to_charge,
                        'price_unit': moto_unit_excl,
                        'product_uom_id': self.product_id.uom_id.id,
                    }
                    if analytic_distribution:
                        line_vals['analytic_distribution'] = analytic_distribution
                    invoice_lines.append((0, 0, line_vals))
                    self.parking_cost = moto_unit_excl * hours_to_charge
                else:
                    from math import ceil
                    if total_minutes <= 60:
                        moto_product = self._get_parking_product('Moto')
                        unit_excl = moto_product.list_price if moto_product else _incl_to_excl(self.product_id, 3100.0)
                        line_vals = {
                            'product_id': self.product_id.id,
                            'name': f'{self.product_id.name} - {self.name} - {self.site_id.name} (Con Sello, 0-60 min)',
                            'quantity': 1,
                            'price_unit': unit_excl,
                            'product_uom_id': self.product_id.uom_id.id,
                        }
                        if analytic_distribution:
                            line_vals['analytic_distribution'] = analytic_distribution
                        invoice_lines.append((0, 0, line_vals))
                        self.parking_cost = unit_excl
                    else:
                        moto_product = self._get_parking_product('Moto')
                        first_unit_excl = moto_product.list_price if moto_product else _incl_to_excl(self.product_id, 3100.0)
                        add_hours = ceil((total_minutes - 60) / 60.0)
                        auto_unit_excl = self.product_id.list_price
                        line_first = {
                            'product_id': self.product_id.id,
                            'name': f'{self.product_id.name} - {self.name} - {self.site_id.name} (Con Sello, 0-60 min)',
                            'quantity': 1,
                            'price_unit': first_unit_excl,
                            'product_uom_id': self.product_id.uom_id.id,
                        }
                        if analytic_distribution:
                            line_first['analytic_distribution'] = analytic_distribution
                        invoice_lines.append((0, 0, line_first))
                        line_add = {
                            'product_id': self.product_id.id,
                            'name': f'{self.product_id.name} - {self.name} - {self.site_id.name} (Con Sello, {add_hours} hora(s) adicionales desde min 61)',
                            'quantity': add_hours,
                            'price_unit': auto_unit_excl,
                            'product_uom_id': self.product_id.uom_id.id,
                        }
                        if analytic_distribution:
                            line_add['analytic_distribution'] = analytic_distribution
                        invoice_lines.append((0, 0, line_add))
                        self.parking_cost = first_unit_excl + auto_unit_excl * add_hours
        else:
            # No sello: precio por hora del producto (mínimo 1)
            # Cobro por hora sin prorrateo: redondeo hacia arriba
            from math import ceil
            try:
                entry_dt = fields.Datetime.from_string(self.check_in)
                out_dt = fields.Datetime.from_string(self.check_out)
                total_minutes = int(((out_dt - entry_dt).total_seconds() + 59) // 60)
            except Exception:
                total_minutes = int(round(self.duration * 60))
            hours_to_charge = max(1, ceil(total_minutes / 60.0))
            quantity = hours_to_charge
            unit_price = self.product_id.list_price
            line_vals = {
                'product_id': self.product_id.id,
                'name': f'{self.product_id.name} - {self.name} - {self.site_id.name} ({quantity:.2f} hours)',
                'quantity': quantity,
                'price_unit': unit_price,
                'product_uom_id': self.product_id.uom_id.id,
            }
            if analytic_distribution:
                line_vals['analytic_distribution'] = analytic_distribution
            invoice_lines.append((0, 0, line_vals))

        if not invoice_lines:
            self.state = 'payment'
            self.paid_bool = True
            self.parking_cost = 0.0
            return False

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'journal_id': journal.id,
            'invoice_date': fields.Date.context_today(self),
            'ref': f'{self.name} - {self.site_id.name}',
            'company_id': self.company_id.id,
            'invoice_line_ids': invoice_lines,
        }
        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice.id
        invoice.action_post()
        return invoice

    def action_create_invoice(self):
        """AcciÃ³n para crear la factura desde la interfaz"""
        invoice = self._create_invoice()
        
        # Abrir la factura creada
        return {
            'name': _('Customer Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_invoice(self):
        """AcciÃ³n para ver la factura asociada"""
        if not self.invoice_id:
            return self.action_create_invoice()
        
        return {
            'name': _('Customer Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_register_payment_improved(self):
        """MÃ©todo mejorado para registrar pago con facturaciÃ³n"""
        # Si no existe factura, crearla primero
        if not self.invoice_id:
            created = self._create_invoice()
            # Si no hay factura (p. ej., Moto <= 30 min con sello), cerrar como pagado
            if not created and self.state == 'payment' and self.paid_bool and self.parking_cost == 0:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
        
        # Validaciones y monto a pagar (sin pagos parciales)
        invoice = self.invoice_id
        if invoice:
            if invoice.amount_residual <= 0:
                raise ValidationError(_('La factura ya estÃ¡ saldada.'))
            if invoice.payment_state in ('in_payment', 'partial', 'paid'):
                raise ValidationError(_('No se permiten pagos parciales o adicionales. Estado: %s') % (invoice.payment_state or 'desconocido'))
        amount_to_pay = invoice.amount_residual if invoice else self.parking_cost
        
        # Abrir nuestro wizard personalizado de registro de pago
        return {
            'name': _('Register Parking Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'register.payment.wizard',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_parking_duration': self.duration,
                'default_amount': amount_to_pay,  # Ahora incluye el IVA
                'default_received_amount': amount_to_pay,
                'default_ref': self.name,
                'default_date': fields.Date.context_today(self),
            },
            'target': 'new',
        }

    @api.depends('invoice_id.payment_state')
    def _compute_payment_status(self):
        """Computed field to automatically update parking entry status based on invoice payment"""
        for record in self:
            if record.invoice_id and record.invoice_id.payment_state == 'paid':
                if record.state != 'payment':
                    record.state = 'payment'
                    record.paid_bool = True

    def update_payment_status(self):
        """MÃ©todo para actualizar el estado de pago del parking entry"""
        if self.invoice_id and self.invoice_id.payment_state == 'paid':
            if self.state != 'payment':
                self.state = 'payment'
                self.paid_bool = True
                # Log para debugging
                _logger.info(f"Parking entry {self.name} marked as paid")

    @api.model
    def _update_parking_entries_payment_status(self):
        """MÃ©todo para actualizar el estado de parking entries cuando las facturas se paguen"""
        # Buscar parking entries que tengan facturas pagadas pero que no estÃ©n marcadas como pagadas
        parking_entries = self.search([
            ('invoice_id.payment_state', '=', 'paid'),
            ('state', '!=', 'payment')
        ])
        
        for entry in parking_entries:
            entry.update_payment_status()

    def _get_parking_product(self, vehicle_type):
        """Return the correct parking service product by vehicle type.

        - Auto: "Servicio de parqueo Auto"
        - Moto: "Servicio de parqueo Moto"

        Avoids matching "Mensualidad Personal Autorizado" (contains 'Auto' in
        'Autorizado') by prioritizing exact service names and excluding
        'Autorizado' in fallbacks.
        """
        Product = self.env['product.product']
        vt = (vehicle_type or '').strip().lower()

        if 'moto' in vt or 'motorcycle' in vt:
            target_name = 'Servicio de parqueo Moto'
        else:
            # AutomÃ³vil/Automovil/Auto
            target_name = 'Servicio de parqueo Auto'

        # 1) Try exact name match
        product = Product.search([
            ('name', '=', target_name),
            ('type', '=', 'service'),
            ('sale_ok', '=', True)
        ], limit=1)
        if product:
            return product

        # 2) Try ilike full service name (robust to accents/case)
        product = Product.search([
            ('name', 'ilike', target_name),
            ('type', '=', 'service'),
            ('sale_ok', '=', True)
        ], limit=1)
        if product:
            return product

        # 3) Fallback by generic keyword but exclude 'Autorizado'
        if 'moto' in vt or 'motorcycle' in vt:
            product = Product.search([
                ('name', 'ilike', 'moto'),
                ('name', 'not ilike', 'Autorizado'),
                ('type', '=', 'service'),
                ('sale_ok', '=', True)
            ], limit=1)
        else:
            product = Product.search([
                ('name', 'ilike', 'auto'),
                ('name', 'not ilike', 'Autorizado'),
                ('type', '=', 'service'),
                ('sale_ok', '=', True)
            ], limit=1)
        return product

    def action_update_payment_status(self):
        """AcciÃ³n manual para actualizar el estado de pago desde la interfaz"""
        self.update_payment_status()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def write(self, vals):
        """Override write to enforce immutability after draft and update slot availability.

        Once a parking entry leaves 'draft', it becomes read-only for manual edits
        (including admin). We still allow controlled system actions like state changes,
        check-in/out timestamps, payment flags, invoice linkage, and chatter/activities.
        A context key `allow_immutable` can be set by internal flows to bypass checks.
        """
        # Enforce immutability when record is not in draft
        if vals and not self.env.context.get('allow_immutable'):
            # Fields allowed to change in non-draft via system actions
            allowed_fields = {
                'state', 'check_in', 'check_in_bool', 'check_out', 'check_out_bool',
                'paid_bool', 'parking_cost', 'duration', 'invoice_id', 'product_id',
                'payment_id', 'with_stamp', 'reference_id',
                'monthly_contract_id', 'monthly_invoice_id', 'monthly_period',
                'receipt_sequence', 'auto_payment_update'
            }
            # Allow chatter/activity technical fields
            def _is_technical_field(fname):
                return fname.startswith('message_') or fname.startswith('activity_')

            # If any target record is already non-draft, ensure only allowed fields are edited
            non_draft_records = self.filtered(lambda r: r.state != 'draft')
            if non_draft_records:
                disallowed = {f for f in vals.keys() if f not in allowed_fields and not _is_technical_field(f)}
                if disallowed:
                    raise UserError(_(
                        'El registro de parqueo es de solo lectura despuÃ©s de la confirmaciÃ³n. No puede modificar los siguientes campos: %s'
                    ) % ', '.join(sorted(disallowed)))

        # Track old slot_id before changes
        old_slots = {rec.id: rec.slot_id for rec in self}

        result = super().write(vals)

        # Update slot availability if state or slot_id changed
        if 'state' in vals or 'slot_id' in vals:
            affected_slots = set()
            for rec in self:
                if rec.slot_id:
                    affected_slots.add(rec.slot_id)
                old_slot = old_slots.get(rec.id)
                if old_slot and old_slot != rec.slot_id:
                    affected_slots.add(old_slot)
            for slot in affected_slots:
                slot.refresh_availability()

        return result

    def unlink(self):
        """Prevent deleting non-draft parking entries."""
        non_draft = self.filtered(lambda r: r.state != 'draft')
        if non_draft and not self.env.context.get('allow_immutable'):
            raise UserError(_('You can only delete parking entries in Draft state.'))
        return super().unlink()

    def _get_default_partner(self):
        """Get default partner 'Cliente Final' for parking entries"""
        partner = self.env['res.partner'].search([('name', '=', 'Consumidor Final')], limit=1)
        if not partner:
            # Si no existe, crear el contacto 'Cliente Final'
            partner = self.env['res.partner'].create({
                'name': 'Consumidor Final',
                'is_company': False,
                'customer_rank': 1,
                'supplier_rank': 0,
            })
            _logger.info("Created default partner 'Consumidor Final' for parking entries")
        return partner.id if partner else False

    # ...existing code...

    @api.model
    def _migrate_existing_entries_to_public(self):
        """MÃ©todo para migrar entradas existentes a customer_type='public'"""
        entries_to_update = self.search([('customer_type', '!=', 'public')])
        if entries_to_update:
            count = len(entries_to_update)
            _logger.info(f"Migrating {count} parking entries to customer_type='public'")
            # Usar SQL directo para evitar trigger del constraint
            self.env.cr.execute("""
                UPDATE parking_entry 
                SET customer_type = 'public' 
                WHERE customer_type IS DISTINCT FROM 'public'
            """)
            _logger.info(f"Successfully migrated {count} parking entries to public type")
        else:
            _logger.info("No parking entries need migration - all are already 'public'")

    @api.model
    def _fix_deprecated_menus(self):
        """MÃ©todo para desactivar menÃºs y acciones deprecadas"""
        try:
            # Desactivar menÃº privado
            private_menu = self.env.ref('odoo_parking_management.parking_entry_menu_private_parking', raise_if_not_found=False)
            if private_menu and private_menu.active:
                private_menu.active = False
                _logger.info("Disabled deprecated private parking menu")
            
            # Desactivar acciÃ³n privada
            private_action = self.env.ref('odoo_parking_management.parking_entry_action_private_parking_entry', raise_if_not_found=False)
            if private_action and private_action.active:
                private_action.active = False
                _logger.info("Disabled deprecated private parking action")
            
            # Asegurar que el menÃº pÃºblico estÃ© activo y sea el principal
            public_menu = self.env.ref('odoo_parking_management.parking_entry_menu_public_parking', raise_if_not_found=False)
            if public_menu:
                public_menu.write({
                    'active': True,
                    'sequence': 5,
                    'name': 'Parking Entry'
                })
                _logger.info("Ensured public parking menu is active and primary")
            
        except Exception as e:
            _logger.error(f"Error fixing deprecated menus: {e}")

    # TODO(deprecate): remove customer_type completely in future version

    def _update_slot_availability(self):
        """Update slot availability when parking entry state changes"""
        if self.slot_id:
            # Force refresh of slot availability
            self.slot_id.refresh_availability()

    @api.onchange('vehicle_id')
    def onchange_vehicle_id(self):
        """Auto-select slot_type_id based on vehicle_name (Moto/AutomÃ³vil)"""
        if self.vehicle_id and self.vehicle_id.vehicle_name:
            vehicle_name = self.vehicle_id.vehicle_name.strip()
            
            # Buscar el slot type que coincida con el vehicle_name
            if vehicle_name in ['Moto', 'AutomÃ³vil', 'Automovil']:  # Incluir variantes
                if vehicle_name == 'Moto':
                    # Buscar slot type para Moto
                    slot_type = self.env['slot.type'].search([
                        ('vehicle_type', '=', 'Moto')
                    ], limit=1)
                elif vehicle_name in ['AutomÃ³vil', 'Automovil']:
                    # Para automÃ³viles, buscar primero con el nombre exacto del vehÃ­culo
                    slot_type = self.env['slot.type'].search([
                        ('vehicle_type', '=', vehicle_name)
                    ], limit=1)
                    
                    # Si no encuentra con el nombre exacto, buscar alternativas comunes
                    if not slot_type:
                        for alt_name in ['AutomÃ³vil', 'Automovil', 'Auto']:
                            if alt_name != vehicle_name:  # No buscar el mismo nombre otra vez
                                slot_type = self.env['slot.type'].search([
                                    ('vehicle_type', '=', alt_name)
                                ], limit=1)
                                if slot_type:
                                    break
                
                if slot_type:
                    self.slot_type_id = slot_type
                    # Limpiar slot_id para que se actualice con el nuevo dominio
                    self.slot_id = False
                    
                    # Asignar automÃ¡ticamente el producto basado en el tipo de slot
                    self.product_id = self._get_parking_product(slot_type.vehicle_type)
        else:
            # Si no hay vehÃ­culo seleccionado, limpiar slot_type_id y slot_id
            self.slot_type_id = False
            self.slot_id = False

    @api.onchange('vehicle_number')
    def _onchange_vehicle_number(self):
        """Cuando el operador digite la placa, intentar vincular el vehÃ­culo existente
        para que el onchange de vehicle_id pueda inferir el tipo de vehÃ­culo.
        Esto soporta la vista simplificada donde solo se muestra 'Placa'.
        """
        if self.vehicle_number and not self.vehicle_id:
            vehicle = self.env['vehicle.details'].search([
                ('number_plate', '=', self.vehicle_number)
            ], limit=1)
            if vehicle:
                self.vehicle_id = vehicle
        # Aplicar lÃ³gica de Personal Autorizado basada en la placa
        return self._apply_authorized_partner_from_plate()

    @api.depends('partner_id', 'site_id', 'created_date')
    def _compute_is_monthly(self):
        """Compute if this entry belongs to a monthly contract"""
        for entry in self:
            if entry.partner_id and entry.site_id:
                # Buscar contrato activo por partner+site
                contract = self.env['parking.monthly.contract'].find_active_contract(
                    entry.partner_id.id,
                    entry.site_id.id,
                    entry.created_date.date() if entry.created_date else fields.Date.today()
                )
                # Validar que la placa pertenezca al contrato (si hay placa)
                plate_ok = False
                if contract and entry.vehicle_number:
                    norm = entry._normalize_plate(entry.vehicle_number)
                    plate_contract = self.env['parking.monthly.contract'].find_contract_by_plate(
                        entry.site_id.id, norm, entry.created_date.date() if entry.created_date else fields.Date.today()
                    )
                    plate_ok = bool(plate_contract and plate_contract.id == contract.id)
                elif contract and not entry.vehicle_number:
                    # Sin placa, no consideramos mensualidad por seguridad
                    plate_ok = False

                if contract and plate_ok:
                    entry.is_monthly = True
                    entry.monthly_contract_id = contract.id
                    entry.monthly_period = contract.get_period_string(
                        entry.created_date.date() if entry.created_date else fields.Date.today()
                    )
                else:
                    entry.is_monthly = False
                    entry.monthly_contract_id = False
                    entry.monthly_period = False
            else:
                entry.is_monthly = False
                entry.monthly_contract_id = False
                entry.monthly_period = False

    @api.constrains('monthly_contract_id', 'monthly_invoice_id')
    def _check_monthly_invoice_assignment(self):
        """Validate monthly invoice assignment"""
        for entry in self:
            if entry.is_monthly and entry.state in ('check_out', 'payment'):
                # Monthly entries should eventually have a monthly invoice
                # This is enforced by the aggregation process, not here
                pass

    # ------------------------------------------------------------------
    # Personal Autorizado (por placa) y control de cupos
    # ------------------------------------------------------------------
    @api.model
    def _normalize_plate(self, plate):
        if not plate:
            return False
        return ''.join(str(plate).upper().strip().split())

    # ------------------------------------------------------------------
    # Vehículos Sospechosos
    # ------------------------------------------------------------------
    def _find_suspicious_alerts(self):
        """Devuelve alertas aplicables para la placa/sede actual.

        Criterios:
        - Coincidencia exacta por placa normalizada y compañía.
        - Activas únicamente.
        - Alcance: aplica si la alerta es para todas las sedes o incluye la sede actual.
        """
        self.ensure_one()
        plate = self.vehicle_number or ''
        norm = self._normalize_plate(plate)
        if not norm:
            return self.env['parking.suspicious.vehicle']
        domain = [
            ('active', '=', True),
            ('vehicle_number_normalized', '=', norm),
            ('company_id', '=', self.company_id.id),
        ]
        alerts = self.env['parking.suspicious.vehicle'].search(domain)
        if not alerts:
            return alerts
        if self.site_id:
            alerts = alerts.filtered(lambda a: a.apply_to_all_sites or not a.site_ids or self.site_id in a.site_ids)
        else:
            alerts = alerts.filtered(lambda a: a.apply_to_all_sites or not a.site_ids)
        return alerts

    def _build_suspicious_warning(self, alerts):
        if not alerts:
            return None
        info_alerts = alerts.filtered(lambda a: a.print_ticket)
        block_alerts = alerts.filtered(lambda a: not a.print_ticket)
        lines = []
        if info_alerts:
            lines.append(_('Alerta informativa: se encontró registro de vehículo sospechoso.'))
            for a in info_alerts:
                if a.reason:
                    lines.append('- %s' % a.reason)
        if block_alerts:
            lines.append(_('Bloqueo: esta placa tiene restricción de ingreso.'))
            for a in block_alerts:
                if a.reason:
                    lines.append('- %s' % a.reason)
        message = '\n'.join(lines) if lines else _('Vehículo sospechoso detectado.')
        return {
            'title': _('Alerta de Vehículo Sospechoso'),
            'message': message,
        }

    def _apply_authorized_partner_from_plate(self):
        """Aplica la lÃ³gica de 'Personal Autorizado' usando la placa digitada.

        - Si la placa estÃ¡ autorizada en la sede y NO excede cupos: asigna partner del contrato.
        - Si la placa estÃ¡ autorizada pero excede cupos: vuelve a 'Consumidor Final' y muestra alerta.
        - Si la placa no estÃ¡ autorizada: mantiene 'Consumidor Final'.

        Retorna dict opcional con 'warning' para onchanges.
        """
        if not self.site_id:
            return
        warning = None
        plate = self.vehicle_number or ''
        norm = self._normalize_plate(plate)
        if not norm:
            # Limpiar a consumidor final si no hay placa
            self.partner_id = self._get_default_partner()
            self.monthly_contract_id = False
            self.is_monthly = False
            self.monthly_period = False
            return
        contract_model = self.env['parking.monthly.contract']
        contract = contract_model.find_contract_by_plate(self.site_id.id, norm, fields.Date.context_today(self))
        default_partner_id = self._get_default_partner()
        if contract:
            # Controlar cupos actuales
            current_inside = contract.get_current_inside_count()
            if current_inside >= max(0, contract.acquired_slots or 0):
                # Excede cupos: asignar consumidor final y advertir
                self.partner_id = default_partner_id
                self.monthly_contract_id = False
                self.is_monthly = False
                self.monthly_period = False
                warning = {
                    'title': _('Cupos Excedidos'),
                    'message': _(
                        'La placa %s pertenece a "%s" pero todos los %s cupos estÃ¡n ocupados. '
                        'Se registrarÃ¡ como cliente ordinario (Consumidor Final).'
                    ) % (plate, contract.partner_id.display_name, contract.acquired_slots)
                }
            else:
                # Dentro de cupos: asignar el contacto del contrato
                self.partner_id = contract.partner_id.id
                # Configurar vÃ­nculo mensual para impresiÃ³n y control
                self.monthly_contract_id = contract.id
                self.is_monthly = True
                self.monthly_period = contract.get_period_string(fields.Date.context_today(self))
        else:
            # No autorizado: consumidor final
            self.partner_id = default_partner_id
            self.monthly_contract_id = False
            self.is_monthly = False
            self.monthly_period = False

        if warning:
            res = {'warning': warning}
        else:
            res = None

        # Agregar advertencia visual por Vehículos Sospechosos (si aplica)
        try:
            alerts = self._find_suspicious_alerts()
        except Exception:
            alerts = self.env['parking.suspicious.vehicle']
        warn2 = self._build_suspicious_warning(alerts)
        if warn2:
            if res and 'warning' in res and res['warning']:
                # Combinar mensajes en un solo warning
                combined = res['warning'].copy()
                combined['message'] = (combined.get('message') or '') + '\n\n' + warn2.get('message')
                res['warning'] = combined
            else:
                res = {'warning': warn2}
        return res

    def _enforce_authorized_quota_before_checkin(self):
        """Valida/ajusta el partner por placa justo antes del check-in y aplica cupos.

        Si la placa estÃ¡ autorizada pero supera cupos, se fuerza a Consumidor Finaly se agrega un mensaje en el chatter.
        """
        if not self.site_id:
            return
        plate = self.vehicle_number or ''
        norm = self._normalize_plate(plate)
        contract_model = self.env['parking.monthly.contract']
        contract = contract_model.find_contract_by_plate(self.site_id.id, norm, fields.Date.context_today(self))
        if not contract:
            # Asegurar Consumidor Final si no autorizado
            self.partner_id = self._get_default_partner()
            self.monthly_contract_id = False
            self.is_monthly = False
            self.monthly_period = False
            return
        # Hay contrato por placa
        current_inside = contract.get_current_inside_count()
        if current_inside >= max(0, contract.acquired_slots or 0):
            # Forzar como ordinario (Consumidor Final) y notificar
            self.partner_id = self._get_default_partner()
            self.monthly_contract_id = False
            self.is_monthly = False
            self.monthly_period = False
            self.message_post(body=_('Cupos excedidos para %s (%s). Entrada registrada como cliente ordinario.') % (
                contract.partner_id.display_name, plate
            ))
        else:
            # Asignar datos de mensualidad
            self.partner_id = contract.partner_id.id
            self.monthly_contract_id = contract.id
            self.is_monthly = True
            self.monthly_period = contract.get_period_string(fields.Date.context_today(self))

    # ------------------------------------------------------------------
    # Printing
    # ------------------------------------------------------------------
    def action_print_ticket(self):
        """Imprime el tiquete segun si es Personal Autorizado o no.

        - Si pertenece a una mensualidad (is_monthly=True), usa el formato
          corto y su paperformat.
        - En caso contrario, usa el tiquete por defecto.
        Se deja como un unico punto de entrada para que en la UI solo
        aparezca una opcion de imprimir.
        """
        self.ensure_one()
        if self.is_monthly and self.monthly_contract_id:
            report = self.env.ref('odoo_parking_management.report_parking_ticket_authorized').sudo()
        else:
            report = self.env.ref('odoo_parking_management.report_parking_ticket').sudo()
        return report.report_action(self)
