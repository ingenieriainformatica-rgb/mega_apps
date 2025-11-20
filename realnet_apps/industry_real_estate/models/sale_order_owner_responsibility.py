from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SaleOrderOwnerResponsibility(models.Model):
    _name = 'sale.order.owner.responsibility'
    _description = 'Responsabilidades económicas (propietarios)'
    _order = 'sequence, id'

    order_id = fields.Many2one('sale.order', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)

    owner_id = fields.Many2one('res.partner', string="Propietario", required=True)
    percent = fields.Float(string="Porcentaje", required=True)
    subject_to_vat = fields.Boolean(string="Maneja IVA")
    is_copropietario = fields.Boolean(string="Copropietario")
    is_main_payee = fields.Boolean(string="Recibe el dinero")
    amount_estimated = fields.Monetary(string="Estimado", currency_field='currency_id', compute='_compute_amount')
    currency_id = fields.Many2one(related='order_id.currency_id', store=True, readonly=True)

    @api.depends('percent', 'order_id.amount_owner_base')
    def _compute_amount(self):
        for l in self:
            if not l.exists():
                continue
            l.amount_estimated = (l.order_id.amount_owner_base or 0.0) * (l.percent or 0.0) / 100.0

    # @api.constrains('order_id', 'percent')
    def _check_total(self):
        for l in self:
            if l.order_id.ecoerp_scope == 'owner':
                total = sum(l.order_id.owner_responsibility_ids.mapped('percent'))
                if total and abs(total - 100.0) > 0.01:
                    raise ValidationError(_("La suma de porcentajes debe ser 100%."))
                
    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        if self.env.context.get('skip_owner_sync'):
            return recs
        for r in recs:
            acc = r.order_id.x_account_analytic_account_id
            if r.order_id.ecoerp_scope == 'owner' and acc:
                # si no existe en la propiedad, crearlo
                exists = acc.owner_line_ids.exists().filtered(lambda l: l.owner_id == r.owner_id)
                if not exists:
                    self.env['account.analytic.account.owner.line'].with_context(skip_owner_sync=True).create({
                        'analytic_account_id': acc.id,
                        'owner_id': r.owner_id.id,
                        'participation_percent': r.percent or 0.0,
                        'iva': r.subject_to_vat or False,
                        'is_main_payee': getattr(r, 'is_main_payee', False),
                    })
        return recs

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('skip_owner_sync'):
            return res
        fields_map = {}
        if 'percent' in vals:
            fields_map['participation_percent'] = 'percent'
        if 'subject_to_vat' in vals:
            fields_map['iva'] = 'subject_to_vat'
        if not fields_map:
            return res
        for r in self:
            acc = r.order_id.x_account_analytic_account_id
            if r.order_id.ecoerp_scope != 'owner' or not acc:
                continue
            line = acc.owner_line_ids.exists().filtered(lambda l: l.owner_id == r.owner_id)
            if line:
                updates = {prop: getattr(r, src) for prop, src in fields_map.items()}
                line.with_context(skip_owner_sync=True).write(updates)
        return res
