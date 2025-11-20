from odoo import api, fields, models


class StockReservationHold(models.Model):
    _name = 'stock.reservation.hold'
    _description = 'Stock Reservation Hold (technical)'
    _order = 'id desc'

    name = fields.Char(string='Referencia', default=lambda self: self._default_name())
    product_id = fields.Many2one('product.product', string='Producto', required=True, index=True)
    location_id = fields.Many2one('stock.location', string='Ubicación', required=True, index=True)
    qty_reserved = fields.Float(string='Cantidad Reservada', required=True, default=0.0)
    reservation_id = fields.Many2one('pos.reservation', string='Reserva POS', ondelete='cascade', index=True)
    state = fields.Selection([
        ('active', 'Activo'),
        ('released', 'Liberado'),
        ('cancelled', 'Cancelado'),
    ], default='active', required=True)
    company_id = fields.Many2one('res.company', related='reservation_id.company_id', store=True, readonly=True)

    def _default_name(self):
        return self.env['ir.sequence'].next_by_code('stock.reservation.hold') or 'HOLD'

    def action_release(self):
        for rec in self.filtered(lambda r: r.state == 'active'):
            rec.state = 'released'


class ProductProduct(models.Model):
    _inherit = 'product.product'

    layaway_qty_reserved = fields.Float(
        string='Qty Reserved for Layaway',
        compute='_compute_layaway_qty_reserved',
        help='Cantidad reservada por apartados (holds) activos.'
    )

    def _compute_layaway_qty_reserved(self):
        Hold = self.env['stock.reservation.hold']
        for prod in self:
            # To avoid subqueries in compute, use read_group which is efficient
            res = Hold.read_group(
                [('product_id', '=', prod.id), ('state', '=', 'active')],
                ['qty_reserved:sum'], ['product_id']
            )
            qty = res and res[0].get('qty_reserved_sum') or 0.0
            prod.layaway_qty_reserved = qty
