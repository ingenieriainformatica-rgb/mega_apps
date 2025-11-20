from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ConfirmReceptionWizard(models.TransientModel):
    _name = 'confirm.reception.wizard'
    _description = 'Confirmación de recepción sin validar'

    order_id = fields.Many2one('sale.order', string='Contrato')
    company_id = fields.Many2one('res.company', string="Organización")
    partner_id = fields.Many2many(
        'res.partner',
        'wizard_partner_rel',
        'wizard_id',
        'partner_id',
        string="Arrendatarios"
    )
    co_partner_id = fields.Many2many(
        'res.partner',
        'wizard_copartner_rel',
        'wizard_id',
        'copartner_id',
        string="Deudores solidarios"
    )
    
    responsible_ids = fields.Many2many(
        'res.partner',
        'wizard_responsible_rel',
        'wizard_id',
        'partner_id',
        string="Responsables del/los productos"
    )
    
    company_partner_id = fields.Many2one(
        'res.partner',
        compute='_compute_company_partner_id',
        string='Partner de la Compañía',
        store=False,
    )
    product_id = fields.Many2one('product.template', string='Producto', domain="[('ecoerp_ok', '=', True)]")
    
    received_quantity = fields.Integer(
        string="Cantidad Recibida", 
        related='order_id.x_delivery_card_line_ids.received_quantity'
    )
    
    @api.depends('company_id')
    def _compute_company_partner_id(self):
        for wizard in self:
            if not wizard.exists():
                continue
            wizard.company_partner_id = wizard.company_id.partner_id.id if wizard.company_id else False

    def confirm_force_received(self):
        """Proceso que confirma la recepción de productos y asigna responsables."""
        self.ensure_one()

        # Validaciones básicas
        if not self.responsible_ids:
            raise UserError("Debes seleccionar al menos un responsable.")
        if not self.company_partner_id:
            raise UserError("La compañía seleccionada no tiene un partner asociado válido.")
        
        # Validación opcional si la compañía es responsable
        if self.company_partner_id in self.responsible_ids:
            pass  # Aquí puedes agregar lógica especial si quieres

        # Iterar por cada producto en el wizard
        for record in self:
            # Buscar todas las líneas de entrega que correspondan al contrato y producto
            delivery_lines = self.env['x.delivery.reception.line'].search([
                ('sale_order_id', '=', record.order_id.id),
                ('product_id', 'in', record.order_id.x_delivery_card_line_ids.mapped('product_id').ids),
            ])
            
            if not delivery_lines:
                raise UserError(f"No se encontró la línea de entrega para el producto {record.product_id.display_name}.")
            
            # Iterar sobre las líneas encontradas
            for delivery_line in delivery_lines:
                # Actualizar la cantidad recibida
                delivery_line.received_quantity = record.received_quantity

                # Asignar los responsables del wizard a la línea de entrega
                delivery_line.responsible_ids = [(6, 0, self.responsible_ids.ids)]

                # si no existe validación del item
                if not delivery_line.validated:
                # registrar un historial para trackear cambios
                    self.env['property.item.history'].create_history(
                        property_item=delivery_line.property_item_id,
                        contract=record.order_id,
                        company=record.company_id,
                        user=self.env.user,
                        quantity=0,
                        value=delivery_line.value,
                        condition=delivery_line.condition,
                        notes=f"Responsables asignados: {', '.join(self.responsible_ids.mapped('name'))}",
                        operation_type=delivery_line.operation_type,
                    )

        # Cambiar el estado del contrato
        # self.order_id.write({'x_custom_state': 'received'})
        
        return {'type': 'ir.actions.act_window_close'}
        
    @api.model
    def default_get(self, fields):
        """ Valores por defecto para el formulario de responsables """
        res = super().default_get(fields)
        sale_order = self.env['sale.order'].browse(self.env.context.get('active_id'))
        res['partner_id'] = [(6, 0, sale_order.partner_id.ids)]
        res['company_id'] = sale_order.company_id.id
        res['co_partner_id'] = [(6, 0, sale_order.x_guarant_partner_id.ids)]
        return res
