from odoo import models, fields

class ClauseLineOrder(models.Model):
    _name = 'clause.line.order'
    _description = 'Cláusula del contrato en la orden de venta'
    _order = 'sequence'

    order_id = fields.Many2one('sale.order', string='Orden de Venta', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Secuencia', default=10)
    ident = fields.Char(string='Prefijo')
    clause_id = fields.Many2one('contract.clause', string='Cláusula', required=True)

class ClauseLineTemplate(models.Model):
    _name = 'clause.line'
    _description = 'Línea de cláusula de plantilla'
    _order = 'sequence'

    template_id = fields.Many2one('contract.template', string='Plantilla', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Secuencia', default=10)
    ident = fields.Char(string='Prefijo')
    clause_id = fields.Many2one('contract.clause', string='Cláusula', required=True)