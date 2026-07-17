# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FleetRepairBranch(models.Model):
    _name = 'fleet.repair.branch'
    _description = 'Configuración de Secuencia por Sede'
    _order = 'customer_type'

    name = fields.Char(string='Nombre de la Sede', required=True)
    customer_type = fields.Selection(
        [
            ('renting', 'Renting'),
            ('particular', '1a1'),
            ('corporate', 'MegaSur'),
        ],
        string='Tipo de Sede',
        required=True,
    )
    sequence_prefix = fields.Char(string='Prefijo OT', required=True, size=5)
    sequence_padding = fields.Integer(string='Dígitos del consecutivo', default=4, required=True)
    sequence_id = fields.Many2one('ir.sequence', string='Secuencia', ondelete='restrict', copy=False)
    next_number = fields.Integer(
        string='Próximo número',
        related='sequence_id.number_next_actual',
        readonly=False,
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Almacén',
        help='Almacén que se asignará automáticamente a las solicitudes de repuestos de esta sede.',
    )

    _sql_constraints = [
        ('customer_type_uniq', 'unique(customer_type)', 'Ya existe una configuración para esta sede.'),
    ]

    def write(self, vals):
        res = super().write(vals)
        if 'sequence_prefix' in vals or 'sequence_padding' in vals:
            for rec in self:
                if rec.sequence_id:
                    rec.sequence_id.sudo().write({
                        'prefix': rec.sequence_prefix,
                        'padding': rec.sequence_padding or 4,
                    })
        return res

    def _ensure_sequence(self):
        self.ensure_one()
        if not self.sequence_prefix:
            raise UserError(_(
                'La sede "%s" no tiene configurado el prefijo de la secuencia de OT.'
            ) % self.name)
        if not self.sequence_id:
            seq = self.env['ir.sequence'].sudo().create({
                'name': 'OT - %s' % self.name,
                'code': 'fleet.repair.%s' % self.customer_type,
                'prefix': self.sequence_prefix,
                'padding': self.sequence_padding or 4,
                'company_id': False,
            })
            self.sudo().sequence_id = seq
        return self.sequence_id

    def _get_next_sequence(self):
        self.ensure_one()
        if not self.sequence_prefix:
            raise UserError(_(
                'La sede "%s" no tiene configurado el prefijo de la secuencia de OT.'
            ) % self.name)
        self._ensure_sequence()
        return self.sequence_id.next_by_id()

    @api.model
    def get_next_for_customer_type(self, customer_type):
        branch = self.search([('customer_type', '=', customer_type)], limit=1)
        if branch:
            return branch._get_next_sequence()
        return self.env['ir.sequence'].next_by_code('fleet.repair') or 'New'
