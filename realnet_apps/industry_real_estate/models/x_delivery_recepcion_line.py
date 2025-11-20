from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from odoo.addons.industry_real_estate import const

class XDeliveryReceptionLine(models.Model):
    _name = 'x.delivery.reception.line'
    _description = 'Línea de entrega/recepción'
    _inherit = ['mail.thread']
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.template', string='Producto', domain="[('ecoerp_ok', '=', True)]")
    description = fields.Text(string='Descripción')
    quantity = fields.Integer(string="Cantidad entregada")
    received_quantity = fields.Integer(string="Cantidad recibida")
    quantity_difference = fields.Integer(string="Diferencia", compute='_compute_difference', store=False)
    condition = fields.Selection(
        const.CONDITION_SELECTION,
        string='Condición',
        default='good'
    )
    date = fields.Datetime(string="Fecha", default=fields.Datetime.now)
    
    validated = fields.Boolean(string="Validado")
    photo = fields.Binary(string="Foto")
    photo_mime = fields.Char(string="Tipo de imagen")
    editable_photo = fields.Boolean(string="¿Foto editable?")
    sale_order_id = fields.Many2one('sale.order', string="Contrato")
    property_item_id = fields.Many2one('property.item', string="Ítem de propiedad")
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        readonly=True,
        store=True
    )

    company_currency_id = fields.Many2one(
        'res.currency',
        string='Moneda de la empresa',
        related='company_id.currency_id',
        readonly=True,
        store=True
    )
    
    value = fields.Monetary(
        string='Valor',
        currency_field='company_currency_id',
        default=0.0,
        help="Valor del item para esta propiedad"
    )
    
    # anexo del historial de inventario para entrega y recepcion
    history_ids = fields.One2many(
        comodel_name='property.item.history',
        inverse_name='property_item_id',
        string='Historial del ítem relacionado',
        compute='_compute_history_ids',
        store=False
    )
    
    operation_type = fields.Char(compute='_compute_operation_type', store=False, default="delivery")
    
    can_add_inventory = fields.Boolean(
        compute='_compute_can_add_inventory',
        store=False,
        string='Puede agregar a inventario'
    )
    
    x_custom_state = fields.Selection(
        related='sale_order_id.x_custom_state',
        string='Estado del contrato',
        store=False,   # o True si quieres guardarlo en DB y poder buscar/filtrar por él
        readonly=True
    )
    
    responsible_ids = fields.Many2many('res.partner', string="Responsables")
    
    @api.depends('sale_order_id.can_add_inventory')
    def _compute_can_add_inventory(self):
        for record in self:
            if not record.exists():
                continue
            record.can_add_inventory = record.sale_order_id.can_add_inventory
    
    @api.depends_context('from_reception', 'from_delivery')
    def _compute_operation_type(self):
        for record in self:
            if not record.exists():
                continue
            if(self.env.context.get('from_reception')):
                record.operation_type = 'reception'
            elif(self.env.context.get('from_delivery')):
                record.operation_type = 'delivery'
            else:
                record.operation_type = 'delivery'
    
    def _compute_history_ids(self):
        for record in self:
            if not record.exists():
                continue
            record.history_ids = record.property_item_id.history_ids if record.property_item_id else False
        
    def action_open_item_history(self):
        self.ensure_one()
        if not self.property_item_id:
            return

        return {
            'type': 'ir.actions.act_window',
            'name': f'Historial de {self.property_item_id.product_id.display_name}',
            'res_model': 'property.item.history',
            'view_mode': 'list,form',
            'domain': [('property_item_id', '=', self.property_item_id.id)],
            'context': {'default_property_item_id': self.property_item_id.id},
            'target': 'current',
        }

    def toggle_validated(self):
        for record in self:
            record.validated = not record.validated
    
    def name_get(self):
        result = []
        for rec in self:
            name = f"{rec.product_id or 'Recepción'} - {rec.date.strftime('%d/%m/%Y') if rec.date else ''}"
            result.append((rec.id, name))
        return result

    @api.depends('quantity', 'received_quantity')
    def _compute_difference(self):
        for rec in self:
            if not rec.exists():
                continue
            cantidad_historial = sum(rec.property_item_id.history_ids.filtered(
                    lambda h: h.operation_type in ['reception', 'delivery']
                ).mapped('quantity'))
            rec.quantity_difference = (cantidad_historial or 0) + (rec.received_quantity or 0) - (rec.quantity or 0)

    @api.onchange('photo')
    def _onchange_photo(self):
        for record in self:
            record.editable_photo = not bool(record.id)
            
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.value = self.product_id.list_price  # O el campo de precio estándar

    @api.model_create_multi
    def create(self, vals_list):
        # 1. Valida que cada registro solo pueda crearse si el contrato está en draft
        for vals in vals_list:
            # sale_order_id puede llegar como id o como False
            sale_order_id = vals.get('sale_order_id')
            if sale_order_id:
                sale_order = self.env['sale.order'].browse(sale_order_id)
                if sale_order.x_custom_state not in ['draft','contract_signed','pending_delivery']:
                    raise UserError("Solo puedes crear ítems de inventario cuando el inventario está abierto.")
        # 2. Crea los registros normalmente
        records = super().create(vals_list)
        # 3. Ejecuta sincronización normalmente
        for record in records:
            record.operation_type = ""
            record._update_property_inventory()
        return records

    def write(self, vals):
        # Validar antes de escribir
        existe_reg = False
        for record in self:
            if not record.sale_order_id.can_add_inventory:# NO puede agregar a inventario
                if self.env.context.get('from_reception'):#validamos contexto actual que solo sea de recepción
                    if set(vals.keys()) == {'validated'}:
                        continue # permitimos continuar cuando es la validación de un producto en recepción
                    if record.sale_order_id.x_custom_state != 'draft':# si el estado es diferente a borrador se restringe la edición
                        allowed_fields = {'received_quantity', 'condition'}
                        if set(vals.keys()).issubset(allowed_fields) and record.sale_order_id.x_custom_state == 'pending_receipt':# solo permitimos editar algunos campos en pendiente recepción para poder recepcionar el producto
                            prop_id = record.property_item_id.property_id.id if record.property_item_id.property_id else False
                            if not prop_id:# validación de registro por propiedad
                                raise UserError("El ítem no tiene asignada una propiedad para registrar el historial.")
                            cantidad_recibida = vals.get('received_quantity', record.received_quantity)
                            entregado = record.sale_order_id.x_delivery_card_line_ids.filtered(
                                lambda l: l.product_id == record.product_id
                            )
                            cantidad_entregada = entregado.quantity if entregado else 0
                            estado_recibido = vals.get('condition', record.condition)
                            estado_recibido = next((t for t in const.CONDITION_SELECTION if t[0] == estado_recibido), None)# traducimos para el registro      
                            cantidad_historial = sum(record.property_item_id.history_ids.filtered(
                                lambda h: h.operation_type == 'reception'
                            ).mapped('quantity'))
                            # validación de control y trazabilididad del histórico de items
                            if cantidad_historial + cantidad_recibida > cantidad_entregada:
                                raise UserError(
                                    f"No se puede recibir más que la cantidad entregada. \n"
                                    f"Entregado: {cantidad_entregada}, ya recibido: {cantidad_historial}, intentado recibir: {cantidad_recibida}"
                                )
                            elif cantidad_entregada >= cantidad_recibida:
                                # registramos historial
                                self.env['property.item.history'].create_history(
                                    property_item=record.property_item_id,
                                    contract=record.sale_order_id,
                                    company=record.company_id,
                                    user=self.env.user,
                                    quantity=cantidad_recibida,
                                    value=record.value,
                                    condition=record.condition,
                                    notes=f"Discrepancia en la cantidad: Entregado {cantidad_entregada}, Recibido {cantidad_recibida} con estado '{estado_recibido[1]}'",
                                    operation_type=record.operation_type,
                                ) #registramos movimiento
                                existe_reg = True # flag para evitar doble movimiento de historial
                            else:
                                raise UserError("La cantidad a recepcionar no puede ser mayor a la entregada.")                        
                        else:
                            raise UserError("No se permite editar un ítem cuando el contrato se ha firmado.")

        # Llamar al método estándar write después de todas las validaciones
        res = super().write(vals)

        # Sincronización de inventario: SOLO si cambias algo que no sea 'validated'
        if (
            not self.env.context.get('skip_item_sync')
            and any(field for field in vals.keys() if field != 'validated')
        ):
            for record in self:
                if(not existe_reg):#evitamos dos registros de historial de inventario adicionales
                    record._update_property_inventory()# registro de movimientos general

        return res

    def _update_property_inventory(self):
        """ Proceso de actualización automática de inventario virtual de propiedades """
        for record in self:
            if self.env.context.get('syncing_from_item'):
                continue

            property_id = False
            contract = record.sale_order_id
            user = self.env.user
            company = self.env.company

            if contract:
                property = contract.x_account_analytic_account_id
                if property:
                    property_id = property.id

            if not (record.product_id and property_id):
                continue  # Evitar errores si falta info

            # Buscar si ya existe el item de inventario
            existing_item = self.env['property.item'].search([
                ('product_id', '=', record.product_id.id),
                ('property_id', '=', property_id),
            ], limit=1)

            vals_item = {
                'quantity': record.quantity,
                'condition': record.condition or existing_item.condition if existing_item else 'good',
                'last_delivery_date': fields.Datetime.now(),
                'photo': record.photo,
                'photo_mime': record.photo_mime,
                'value': record.value,
                'notes': record.description,
            }

            if existing_item:
                existing_item.with_context(skip_delivery_sync=True).write(vals_item)
                if not record.property_item_id:
                    record.property_item_id = existing_item.id
            else:
                new_item = self.env['property.item'].create({
                    **vals_item,
                    'product_id': record.product_id.id,
                    'property_id': property_id,
                })
                record.property_item_id = new_item.id

            # Crear historial automáticamente (autogenera notes)
            self.env['property.item.history'].create_history(
                property_item=record.property_item_id,
                contract=contract if contract else False,
                company=company,
                user=user,
                quantity=record.quantity if self.env.context.get('from_delivery') else 0,
                value=record.value,
                condition=record.condition,
                operation_type=record.operation_type or 'delivery',
            )

    def unlink(self):
        for record in self:
            if record.sale_order_id.x_custom_state != 'draft':
                raise UserError("Solo puedes eliminar ítems de inventario cuando el contrato está en estado borrador.")
        return super().unlink()
    
    def copy(self, default=None):
        raise UserError("No está permitido duplicar un elemento de entrega o recepción.")
    
    def action_open_full_form_delivery(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Entrega',
            'res_model': 'x.delivery.reception.line',
            'view_mode': 'form',
            'res_id': self.id,
            'view_id': self.env.ref('industry_real_estate.view_x_delivery_reception_line_form').id,
            'target': 'current',
            'context': {'from_delivery': True}
        }
        
    def action_open_full_form_reception(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Entrega',
            'res_model': 'x.delivery.reception.line',
            'view_mode': 'form',
            'res_id': self.id,
            'view_id': self.env.ref('industry_real_estate.view_x_delivery_reception_line_form').id,
            'target': 'current',
            'context': {'from_reception': True}
        }
        
    def validate_reception(self):
        for record in self:
            # Verificar si la cantidad entregada y la cantidad recibida coinciden
            entregado = record.x_delivery_card_line_ids.filtered(lambda l: l.product_id == record.product_id)
            cantidad_entregada = entregado.quantity if entregado else 0
            cantidad_recibida = record.received_quantity

            # Si hay discrepancia entre entrega y recepción, generamos un movimiento de historial
            if cantidad_entregada != cantidad_recibida:
                # Crear movimiento en el historial
                self.env['property.item.history'].create_history(
                    property_item=record.property_item_id,
                    company=record.company_id,
                    user=self.env.user,
                    quantity=cantidad_recibida,
                    value=record.value,
                    condition=record.condition,
                    notes=f"Discrepancia en la cantidad: Entregado {cantidad_entregada}, Recibido {cantidad_recibida}",
                    operation_type=record.operation_type,  # Tipo de movimiento
                )

                # Cambiar el estado del contrato si es necesario
                # record.sale_order_id.x_custom_state = 'pendiente_recepcion'

                # Opcional: Puedes agregar más lógicas como notificar o enviar alertas
                
    def action_to_edit_reception(self):
        self.ensure_one()
        readonly_fields = [f for f in self._fields if f not in ('received_quantity', 'condition')]
        return {
            'name': 'Editar Cantidad Recibida',
            'type': 'ir.actions.act_window',
            'res_model': 'x.delivery.reception.line',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',  # ventana completa
            'context': {
                'readonly_fields': readonly_fields,
            },
        }