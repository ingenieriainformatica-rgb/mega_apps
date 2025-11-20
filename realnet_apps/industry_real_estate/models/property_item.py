from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.addons.industry_real_estate import const

class PropertyItem(models.Model):
    _name = 'property.item'
    _description = 'Inventario de items por propiedad (independiente del inventario general)'
    _order = 'product_id, id desc'

    property_id = fields.Many2one(
        'account.analytic.account', 
        string='Propiedad', 
        required=False
    )
    product_id = fields.Many2one(
        'product.template', 
        string='Producto', 
        required=True,
        domain="[('ecoerp_ok', '=', True)]"
    )
    quantity = fields.Integer(
        string='Cantidad', 
        required=True, 
        default=0,
        help="Cantidad disponible en esta propiedad"
    )
    
    condition = fields.Selection(
        const.CONDITION_SELECTION,
        string='Condición',
        default='good'
    )

    purchase_date = fields.Date('Fecha de Compra')
    value = fields.Monetary(
        'Valor', 
        currency_field='company_currency_id', 
        default=0.0,
        help="Valor del item para esta propiedad"
    )
    notes = fields.Text('Observaciones')

    # Nuevos campos sincronizados
    photo = fields.Binary(string="Imagen")
    photo_mime = fields.Char(string="Tipo MIME")

    last_delivery_date = fields.Datetime('Última Entrega', readonly=True)
    last_reception_date = fields.Datetime('Última Recepción', readonly=True)

    company_currency_id = fields.Many2one(
        'res.currency', 
        related='company_id.currency_id', 
        store=True,
        readonly=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True
    )
    
    history_ids = fields.One2many(
        'property.item.history',
        'property_item_id',
        string='Historial de entregas/recepciones'
    )
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.value = self.product_id.list_price  # O el campo que uses como precio estándar

    @api.constrains('quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity < 0:
                raise ValidationError(f"La cantidad no puede ser negativa para {record.product_id.name}")

    @api.model_create_multi
    def create(self, vals_list):
        items = super().create(vals_list)
        for item in items:
            item._sync_to_delivery_line()
        return items

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('skip_delivery_sync'):
            for item in self:
                item._sync_to_delivery_line()
        return res

    def _sync_to_delivery_line(self):
        """
        Sincroniza automáticamente con x.delivery.reception.line (solo entrega).
        """
        DeliveryLine = self.env['x.delivery.reception.line']

        if not self.property_id:
            return

        sale_orders = self.env['sale.order'].search([
            ('x_account_analytic_account_id', '=', self.property_id.id)
        ], limit=1)

        if not sale_orders:
            return

        existing_line = DeliveryLine.search([
            ('sale_order_id', '=', sale_orders.id),
            ('product_id', '=', self.product_id.id)
        ], limit=1)

        if existing_line:
            existing_line.with_context(skip_item_sync=True).write({
                'property_item_id': self.id,
                'quantity': self.quantity,
                'condition': self.condition,
                'description': self.notes or '',
                'photo': self.photo,
                'photo_mime': self.photo_mime,
            })
        else:
            DeliveryLine.create({
                'sale_order_id': sale_orders.id,
                'property_item_id': self.id,
                'product_id': self.product_id.id,
                'quantity': self.quantity,
                'condition': self.condition,
                'description': self.notes or '',
                'photo': self.photo,
                'photo_mime': self.photo_mime,
            })
            
    def action_open_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Historial de {self.product_id.display_name}',
            'res_model': 'property.item.history',
            'view_mode': 'list,form',
            'domain': [('property_item_id', '=', self.id)],
            'context': {
                'default_property_item_id': self.id,
                'default_property_id': self.property_id.id,
            },
            'target': 'current',
        }
        
    def unlink(self):
        related_orders = self.mapped('delivery_line_ids.sale_order_id') | self.mapped('reception_line_ids.sale_order_id')
        res = super().unlink()
        related_orders._compute_can_add_inventory()
        return res
