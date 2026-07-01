# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_ALLOWED_GROUPS = [
    'car_repair_industry.group_fleet_repair_head_technician',
    'car_repair_industry.group_fleet_repair_service_manager',
    'car_repair_industry.group_fleet_repair_directeur_commercial',
]
_TECHNICIAN_GROUP = 'car_repair_industry.group_fleet_repair_portal_technician'
_BLOCKED_REPAIR_STATES = ('done', 'cancel')


class FleetDiagnoseAssigntoTechnician(models.TransientModel):
    _name = 'fleet.diagnose.assignto.technician'
    _description = "Asignación / reasignación de técnico al diagnóstico"

    is_reassignment = fields.Boolean(string='Es reasignación', default=False)
    current_user_id = fields.Many2one(
        'res.users',
        string='Técnico actual',
        readonly=True,
    )
    available_technician_ids = fields.Many2many(
        'res.users',
        compute='_compute_available_technicians',
        string='Técnicos disponibles',
    )
    user_id = fields.Many2one(
        'res.users',
        string='Técnico',
        required=True,
        domain="[('id', 'in', available_technician_ids)]",
    )
    reassign_reason = fields.Char(string='Motivo de reasignación')

    @api.depends('is_reassignment')
    def _compute_available_technicians(self):
        group = self.env.ref(_TECHNICIAN_GROUP)
        users = self.env['res.users'].search([
            ('active', '=', True),
            ('groups_id', 'in', [group.id]),
        ])
        for rec in self:
            rec.available_technician_ids = users

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        is_reassignment = bool(self._context.get('is_reassignment'))
        res['is_reassignment'] = is_reassignment
        if is_reassignment:
            active_id = self._context.get('active_id')
            if active_id:
                diagnose = self.env['fleet.diagnose'].browse(active_id)
                if diagnose.exists() and diagnose.user_id:
                    res['current_user_id'] = diagnose.user_id.id
        return res

    def _check_executor_permission(self):
        """Validates that the user running the action belongs to an authorized group."""
        if not any(self.env.user.has_group(g) for g in _ALLOWED_GROUPS):
            raise UserError(_("No tiene permiso para asignar o reasignar técnicos."))

    def _apply_technician_assignment(self, diagnose, new_user, reason=None):
        """
        Shared logic for initial assignment and reassignment.

        Updates ONLY:
          - fleet.diagnose.user_id
          - fleet.repair.portal_technician_id   (Técnico portal)

        Does NOT touch fleet.repair.user_id (Asignado a) nor any other field.
        All changes execute inside a single transaction; any validation error
        prevents partial writes.
        """
        self._check_executor_permission()

        # ── Diagnose validations ──────────────────────────────────────────────
        if not diagnose or not diagnose.exists():
            raise UserError(_("El diagnóstico no existe."))
        if diagnose.state == 'done':
            raise UserError(_("No es posible asignar técnico en un diagnóstico finalizado."))

        # ── Repair validations ────────────────────────────────────────────────
        repair = diagnose.fleet_repair_id
        if not repair:
            raise UserError(_(
                "El diagnóstico no tiene una orden de reparación relacionada."
            ))
        if repair.state in _BLOCKED_REPAIR_STATES:
            raise UserError(_(
                "No es posible reasignar el técnico en una orden finalizada o cancelada."
            ))

        # ── New technician validations ────────────────────────────────────────
        if not new_user:
            raise UserError(_("Debe seleccionar un técnico."))
        if not new_user.active:
            raise ValidationError(_("El técnico seleccionado está inactivo."))
        if not new_user.has_group(_TECHNICIAN_GROUP):
            raise ValidationError(_(
                "El usuario «%s» no tiene el rol «Portal - Técnico». "
                "Solo pueden asignarse usuarios portal con ese rol."
            ) % new_user.display_name)

        previous_user = diagnose.user_id
        is_reassignment = bool(previous_user)

        # ── Reassignment-specific validations ─────────────────────────────────
        if is_reassignment:
            if new_user == previous_user:
                raise UserError(_("El nuevo técnico es el mismo que el técnico actual."))
            if not reason or not reason.strip():
                raise UserError(_("El motivo de reasignación es obligatorio."))

        # ── Apply changes ─────────────────────────────────────────────────────
        diagnose_vals = {'user_id': new_user.id}
        if not is_reassignment:
            diagnose_vals['state'] = 'in_progress'
        diagnose.write(diagnose_vals)
        repair.write({'portal_technician_id': new_user.id})

        # ── Chatter log (only on reassignment) ───────────────────────────────
        if is_reassignment:
            body = Markup(
                "Técnico reasignado de <b>%s</b> a <b>%s</b>.<br/>"
                "Motivo: %s<br/>"
                "Reasignado por: %s."
            ) % (
                previous_user.display_name,
                new_user.display_name,
                reason.strip(),
                self.env.user.display_name,
            )
            repair.message_post(body=body)

    def do_assign_technician(self):
        self.ensure_one()
        active_id = self._context.get('active_id')
        if not active_id:
            raise UserError(_("No se encontró el diagnóstico activo."))
        diagnose = self.env['fleet.diagnose'].browse(active_id)
        reason = self.reassign_reason if self.is_reassignment else None
        self._apply_technician_assignment(diagnose, self.user_id, reason=reason)
        return {'type': 'ir.actions.act_window_close'}
