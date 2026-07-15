# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError


class FleetRepairRoadTestRequestWizard(models.TransientModel):
    _name = 'fleet.road.test.request.wizard'
    _description = 'Solicitar prueba de ruta'

    repair_id = fields.Many2one(
        'fleet.repair',
        string='Orden de trabajo',
        required=True,
        readonly=True,
    )
    test_type = fields.Selection([
        ('before', 'Antes de la reparación'),
        ('during', 'Durante la reparación'),
        ('after', 'Después de la reparación'),
    ], string='Tipo de prueba', required=True, default='during')
    notes = fields.Text(string='Observación')

    def _check_permissions(self):
        user = self.env.user
        if not (
            user.has_group('car_repair_industry.group_fleet_repair_service_manager')
            or user.has_group('car_repair_industry.group_fleet_repair_directeur_commercial')
        ):
            raise AccessError(_("No tienes permisos para solicitar pruebas de ruta."))

    def action_confirm(self):
        self.ensure_one()
        self._check_permissions()

        repair = self.repair_id
        if not repair.exists():
            raise UserError(_("La orden de trabajo ya no existe."))
        if repair.state == 'cancel':
            raise UserError(_(
                "No se puede solicitar una prueba de ruta para una orden cancelada."
            ))

        # Verificar solicitud activa del mismo tipo para la misma reparación
        duplicate = self.env['fleet.road.test'].search_count([
            ('repair_id', '=', repair.id),
            ('test_type', '=', self.test_type),
            ('state', 'in', ['requested', 'assigned', 'in_progress']),
        ])
        if duplicate:
            type_label = dict(self._fields['test_type'].selection).get(
                self.test_type, self.test_type
            )
            raise UserError(_(
                "Ya existe una solicitud activa de tipo «%s» para esta orden. "
                "Cancélala antes de crear otra del mismo tipo."
            ) % type_label)

        # Crear el registro en fleet.road.test
        self.env['fleet.road.test'].create({
            'repair_id': repair.id,
            'test_type': self.test_type,
            'requested_by_id': self.env.user.id,
            'state': 'requested',
            'request_observation': self.notes or False,
        })

        # Actualizar flujo operativo de la reparación
        repair.write({
            'service_flow_state': 'road_test_requested',
            'road_test_requested_at': fields.Datetime.now(),
            'closure_result': 'requires_road_test',
        })

        # Notificaciones (mismo comportamiento que el método original)
        repair._notify_repair_group(
            'car_repair_industry.group_fleet_repair_service_manager',
            _("Solicitud de prueba de ruta"),
        )
        repair._notify_repair_user(
            repair.road_test_user_id,
            _("Se le asignó una prueba de ruta"),
            _("Orden: %s") % (repair.sequence or repair.display_name),
        )

        return {'type': 'ir.actions.act_window_close'}
