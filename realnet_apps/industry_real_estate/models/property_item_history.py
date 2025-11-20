from odoo import models, fields, api
from odoo.addons.industry_real_estate import const

class PropertyItemHistory(models.Model):
    _name = 'property.item.history'
    _description = 'Historial de movimientos del ítem'

    property_item_id = fields.Many2one('property.item', string='Ítem', required=True, ondelete='cascade')
    contract_id = fields.Many2one('sale.order', string='Contrato')
    product_id = fields.Many2one('product.template', string='Producto', related='property_item_id.product_id', store=True)
    date = fields.Datetime(string='Fecha', default=fields.Datetime.now)
    operation_type = fields.Selection([
        ('delivery', 'Entrega'),
        ('reception', 'Recepción'),
        ('manual', 'Actualización manual'),
    ], string='Tipo de operación', required=True)
    quantity = fields.Integer(string='Cantidad')
    condition = fields.Selection(
        const.CONDITION_SELECTION,
        string='Condición',
        default='good'
    )
    value = fields.Monetary(string='Valor')
    user_id = fields.Many2one('res.users', string='Responsable', default=lambda self: self.env.user)
    currency_id = fields.Many2one('res.currency', related='property_item_id.company_currency_id', readonly=True)
    notes = fields.Text(string='Notas')
    property_id = fields.Many2one(
        'account.analytic.account',
        string='Propiedad',
        required=True,
        ondelete='cascade'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            user = self.env.user
            property_name = ''
            contract_name = ''
            
            # Detectar tipo de operación desde el contexto
            if 'operation_type' not in vals:
                context = self.env.context
                if context.get('from_reception'):
                    vals['operation_type'] = 'reception'
                else:
                    vals['operation_type'] = 'delivery'
            # Autogenerar nota descriptiva si no se especifica
            if not vals.get('notes'):
                propiedad = self.env['account.analytic.account'].browse(vals.get('property_id')).name if vals.get('property_id') else ''
                contrato = self.env['sale.order'].browse(vals.get('contract_id')).name if vals.get('contract_id') else ''
                vals['notes'] = f"Movimiento realizado por el usuario {user.name} asociado al contrato {contrato} de la propiedad {propiedad}"

            # Buscar propiedad si viene referenciada
            if vals.get('property_id'):
                property_rec = self.env['account.analytic.account'].browse(vals['property_id'])
                property_name = property_rec.name or ''

                # Si hay contrato asociado a la propiedad (si aplica), ejemplo (ajústalo a tu lógica)
                contract = self.env['sale.order'].search([('property_id', '=', property_rec.id)], limit=1)
                if contract:
                    contract_name = contract.name or ''

            # Generar descripción automática
            descripcion = f"Acción realizada por el usuario {user.name}  desde la vista  {self.env.context.get('view_mode', 'Desconocida')}"
            if property_name:
                descripcion += f" sobre la propiedad '{property_name}'"
            if contract_name:
                descripcion += f", relacionado al contrato '{contract_name}'"

            # Solo asignar si no se ingresó manualmente
            vals.setdefault('notes', descripcion)

            # Garantizar valores clave
            vals.setdefault('user_id', user.id)
            vals.setdefault('company_id', user.company_id.id)

        return super(PropertyItemHistory, self).create(vals_list)

    @api.model
    def create_history(self, property_item, contract=None, company=None, user=None,
                        quantity=None, value=None, condition=None, notes='', operation_type='delivery',
                        only_if_not_validated=False):
        """
        Método centralizado para crear un historial de movimientos.

        :param property_item: record de property.item relacionado
        :param contract: record de contrato (sale.order)
        :param company: record de compañía
        :param user: usuario responsable
        :param quantity: cantidad a registrar
        :param value: valor del ítem
        :param condition: estado del ítem
        :param notes: texto de notas adicionales
        :param operation_type: tipo de movimiento
        :param only_if_not_validated: si True, solo crea registro si el ítem no está validado
        """
        # Validación de cantidad solo si aplica
        if only_if_not_validated and getattr(property_item, 'validated', False):
            return False  # no crea registro

        data = {
            'property_item_id': property_item.id,
            'property_id': property_item.property_id.id,
            'contract_id': contract.id if contract else False,
            'company_id': company.id if company else False,
            'user_id': user.id if user else self.env.user.id,
            'quantity': quantity or 0,
            'value': value or property_item.value,
            'condition': condition or property_item.condition,
            'notes': notes,
            'operation_type': operation_type,
        }
        return self.create(data)