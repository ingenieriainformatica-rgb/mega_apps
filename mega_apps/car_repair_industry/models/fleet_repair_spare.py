# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class FleetRepairSpareCatalog(models.Model):
    _name = 'fleet.repair.spare.catalog'
    _description = 'Catálogo de repuestos genéricos'
    _order = 'name asc'
    _rec_name = 'name'

    name = fields.Char(string='Nombre del repuesto', required=True, index=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        (
            'name_unique',
            'unique(name)',
            'Ya existe un repuesto con este nombre en el catálogo.',
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name'):
                vals['name'] = vals['name'].strip().upper()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('name'):
            vals['name'] = vals['name'].strip().upper()
        return super().write(vals)

    @api.constrains('name')
    def _check_name_not_empty(self):
        for rec in self:
            if not (rec.name or '').strip():
                raise ValidationError(_("El nombre del repuesto no puede estar vacío."))


class FleetRepairSpareRequest(models.Model):
    _name = 'fleet.repair.spare.request'
    _description = 'Solicitud de repuestos para cotizar'
    _order = 'request_date desc, id desc'
    _inherit = ['mail.thread']

    repair_id = fields.Many2one(
        'fleet.repair',
        string='Orden de taller',
        required=True,
        ondelete='cascade',
        index=True,
    )
    repair_sequence = fields.Char(
        related='repair_id.sequence', string='# Orden', store=False,
    )
    requested_by_id = fields.Many2one(
        'res.users',
        string='Técnico solicitante',
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
    )
    request_date = fields.Datetime(
        string='Fecha de solicitud',
        default=fields.Datetime.now,
        readonly=True,
    )
    state = fields.Selection(
        [
            ('requested', 'Solicitado'),
            ('reviewed', 'Revisado'),
            ('cancelled', 'Cancelado'),
        ],
        string='Estado',
        default='requested',
        required=True,
        tracking=True,
    )
    warehouse_note = fields.Text(string='Observación de almacén')
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        index=True,
    )
    line_ids = fields.One2many(
        'fleet.repair.spare.request.line',
        'request_id',
        string='Repuestos solicitados',
    )
    line_count = fields.Integer(
        string='Cant. repuestos',
        compute='_compute_line_count',
        store=True,
    )

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    def action_mark_reviewed(self):
        for rec in self:
            if rec.state != 'requested':
                label = dict(self._fields['state'].selection).get(rec.state, rec.state)
                raise UserError(_(
                    "Solo se pueden revisar solicitudes en estado 'Solicitado'.\n"
                    "Estado actual: %s"
                ) % label)
            rec.write({'state': 'reviewed'})
        return True


class FleetRepairSpareRequestLine(models.Model):
    _name = 'fleet.repair.spare.request.line'
    _description = 'Línea de solicitud de repuesto'
    _order = 'id asc'

    request_id = fields.Many2one(
        'fleet.repair.spare.request',
        string='Solicitud',
        required=True,
        ondelete='cascade',
        index=True,
    )
    spare_catalog_id = fields.Many2one(
        'fleet.repair.spare.catalog',
        string='Repuesto',
        required=True,
    )
    quantity = fields.Float(
        string='Cantidad',
        required=True,
        default=1.0,
    )
    technician_note = fields.Text(string='Observación del técnico')
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        related='request_id.company_id',
        store=True,
    )

    @api.constrains('quantity')
    def _check_quantity(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError(_("La cantidad debe ser mayor que cero."))


class FleetRepairSpareExt(models.Model):
    """Extends fleet.repair with spare request relationship."""
    _inherit = 'fleet.repair'

    spare_request_ids = fields.One2many(
        'fleet.repair.spare.request',
        'repair_id',
        string='Solicitudes de repuestos',
    )
    spare_request_count = fields.Integer(
        string='Solicitudes repuestos',
        compute='_compute_spare_request_count',
        store=True,
    )

    @api.depends('spare_request_ids')
    def _compute_spare_request_count(self):
        for rec in self:
            rec.spare_request_count = len(rec.spare_request_ids)

    def action_view_spare_requests(self):
        self.ensure_one()
        return {
            'name': _('Solicitudes de repuestos'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.repair.spare.request',
            'view_mode': 'list,form',
            'domain': [('repair_id', '=', self.id)],
            'context': {'default_repair_id': self.id},
        }
