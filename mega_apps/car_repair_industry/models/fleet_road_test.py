# -*- coding: utf-8 -*-
from odoo import api, fields, models


class FleetRoadTest(models.Model):
    _name = 'fleet.road.test'
    _description = 'Prueba de Ruta'
    _order = 'requested_at desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    repair_id = fields.Many2one(
        'fleet.repair', string='Orden de trabajo',
        required=True, ondelete='cascade', index=True,
    )
    test_type = fields.Selection([
        ('before', 'Antes de la reparación'),
        ('during', 'Durante la reparación'),
        ('after', 'Después de la reparación'),
    ], string='Tipo de prueba', required=True, default='after')
    requested_by_id = fields.Many2one(
        'res.users', string='Solicitado por',
        required=True, readonly=True, default=lambda self: self.env.user,
    )
    requested_at = fields.Datetime(
        string='Fecha de solicitud', required=True, readonly=True,
        default=fields.Datetime.now,
    )
    driver_id = fields.Many2one(
        'res.users',
        string='Conductor/Responsable asignado',
        tracking=True,
        domain=lambda self: [('groups_id', 'in', self.env.ref(
            'car_repair_industry.group_fleet_repair_portal_road_test',
            raise_if_not_found=False,
        ).ids or [])],
    )
    state = fields.Selection([
        ('requested', 'Solicitada'),
        ('assigned', 'Asignada'),
        ('in_progress', 'En proceso'),
        ('done', 'Realizada'),
        ('cancelled', 'Cancelada'),
    ], string='Estado', required=True, default='requested', tracking=True, index=True)
    request_observation = fields.Text(string='Observación de solicitud')
    result = fields.Text(string='Resultado de la prueba')
    final_observations = fields.Text(string='Observaciones finales')
    completed_at = fields.Datetime(string='Fecha de realización', readonly=True)
    km_start = fields.Float(string='Kilometraje inicial', digits=(10, 1))
    km_end = fields.Float(string='Kilometraje final', digits=(10, 1))

    def action_assign(self):
        self.ensure_one()
        self.write({'state': 'assigned'})

    def action_start(self):
        self.ensure_one()
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.ensure_one()
        self.write({'state': 'done', 'completed_at': fields.Datetime.now()})

    def action_cancel(self):
        self.ensure_one()
        self.write({'state': 'cancelled'})

    def get_state_label(self):
        labels = dict(self._fields['state'].selection)
        return labels.get(self.state, self.state)

    def get_type_label(self):
        labels = dict(self._fields['test_type'].selection)
        return labels.get(self.test_type, self.test_type)
