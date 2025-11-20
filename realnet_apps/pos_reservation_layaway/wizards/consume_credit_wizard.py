from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ConsumeCreditWizard(models.TransientModel):
    _name = 'pos.reservation.consume.credit.wizard'
    _description = 'Consumir saldo a favor del cliente'

    partner_id = fields.Many2one('res.partner', string='Cliente', required=True)
    amount = fields.Monetary('Monto a consumir', required=True)
    journal_id = fields.Many2one('account.journal', string='Diario', domain=[('type', 'in', ['bank', 'cash'])], required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, readonly=True)

    def action_consume(self):
        self.ensure_one()
        if self.amount <= 0:
            raise UserError(_('El monto debe ser mayor a 0.'))
        partner = self.partner_id
        receivable = partner.property_account_receivable_id
        journal = self.journal_id
        # Convert selected credit into a counterpart debit on receivable to clear credit
        move = self.env['account.move'].create({
            'journal_id': journal.id,
            'ref': _('Consumo de crédito (POS)'),
            'line_ids': [
                (0, 0, {
                    'name': _('Consumo de crédito POS'),
                    'partner_id': partner.id,
                    'account_id': receivable.id,
                    'debit': self.amount,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': _('Consumo de crédito POS'),
                    'partner_id': partner.id,
                    'account_id': journal.default_account_id.id,
                    'debit': 0.0,
                    'credit': self.amount,
                }),
            ]
        })
        move.action_post()
        return {'type': 'ir.actions.act_window_close'}

