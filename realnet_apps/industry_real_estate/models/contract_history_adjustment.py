from odoo import api, fields, models


class ContractHistoryAdjustment(models.Model):
    _name = 'contract.history.adjustment'
    _description = 'Historial de Ajustes IPC por Contrato'
    _order = 'adjustment_date desc'

    contract_id = fields.Many2one('x.contract', 'Contrato', required=True, ondelete='cascade')
    ipc_id = fields.Many2one('ipc.history', 'IPC Aplicado', required=True)
    
    adjustment_date = fields.Date('Fecha de Ajuste', required=True, default=fields.Date.today)
    
    # Valores antes y después
    old_rent_amount = fields.Monetary('Valor Anterior')
    new_rent_amount = fields.Monetary('Valor Nuevo')
    currency_id = fields.Many2one('res.currency', related='contract_id.sale_order_id.currency_id', store=True, readonly=True)
    
    # Cálculos
    ipc_percentage = fields.Float('% IPC Aplicado', digits=(16, 4))
    
    # ipc_percentage = fields.Float(
    #     '% IPC Aplicado',
    #     related='ipc_id.variation_annual',
    #     store=True,
    #     readonly=True,
    #     digits=(16, 4)
    # )
    
    
    # adjustment_amount = fields.Monetary('Incremento', compute='_compute_adjustment_amount', store=True)
    adjustment_amount = fields.Monetary('Incremento', store=True)
    
    # Control
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('applied', 'Aplicado'),
        ('cancelled', 'Cancelado')
    ], default='pending', string='Estado')
    
    applied_by = fields.Many2one('res.users', 'Aplicado por')
    notes = fields.Text('Notas')
    active = fields.Boolean('Activo', default=True)

    is_manual_adjustment = fields.Boolean('Ajuste Manual', default=False, help='Marcar si el ajuste no sigue exactamente el IPC')

    # @api.depends('old_rent_amount', 'new_rent_amount')
    # def _compute_adjustment_amount(self):
    #     for record in self:
    #         record.adjustment_amount = record.new_rent_amount - record.old_rent_amount
            
    #         # Calcular el porcentaje REAL aplicado
    #         if record.old_rent_amount:
    #             record.adjustment_percentage_real = (
    #                 (record.new_rent_amount - record.old_rent_amount) / record.old_rent_amount
    #             ) * 100
    #         else:
    #             record.adjustment_percentage_real = 0.0