# -*- coding: utf-8 -*-

from odoo import api, fields, models  #type: ignore


class ResUsers(models.Model):
    _inherit = 'res.users'

    car_repair_portal_profile = fields.Selection(
        selection=[
            ('advisor', 'Asesor de recepción'),
            ('technician', 'Técnico mecánico'),
            ('road_test', 'Técnico de ruta'),
        ],
        string="Perfil portal taller",
        compute='_compute_car_repair_portal_profile',
        inverse='_inverse_car_repair_portal_profile',
        readonly=False,
        help="Perfil de Taller de autos para usuarios portal.",
    )

    car_repair_user_type = fields.Selection(
        selection=[
            ('internal', 'Usuario interno (empleado)'),
            ('portal', 'Usuario portal (cliente / proveedor)'),
        ],
        string='Tipo de usuario (Taller)',
        compute='_compute_car_repair_user_type',
        inverse='_inverse_car_repair_user_type',
        readonly=False,
        precompute=False,
        help='Selecciona si el usuario tiene acceso al backend (interno) o solo al portal. '
             'Reemplaza visualmente al selector USER TYPE de Odoo, que solo se muestra a superusuarios.',
    )

    @api.depends('groups_id')
    def _compute_car_repair_portal_profile(self):
        advisor_group = self.env.ref('car_repair_industry.group_fleet_repair_portal_advisor', raise_if_not_found=False)
        technician_group = self.env.ref('car_repair_industry.group_fleet_repair_portal_technician', raise_if_not_found=False)
        road_test_group = self.env.ref('car_repair_industry.group_fleet_repair_portal_road_test', raise_if_not_found=False)
        for user in self:
            profile = False
            if advisor_group and advisor_group in user.groups_id:
                profile = 'advisor'
            elif technician_group and technician_group in user.groups_id:
                profile = 'technician'
            elif road_test_group and road_test_group in user.groups_id:
                profile = 'road_test'
            user.car_repair_portal_profile = profile

    def _inverse_car_repair_portal_profile(self):
        profile_groups = {
            'advisor': self.env.ref('car_repair_industry.group_fleet_repair_portal_advisor', raise_if_not_found=False),
            'technician': self.env.ref('car_repair_industry.group_fleet_repair_portal_technician', raise_if_not_found=False),
            'road_test': self.env.ref('car_repair_industry.group_fleet_repair_portal_road_test', raise_if_not_found=False),
        }
        portal_groups = profile_groups.values()
        portal_groups = self.env['res.groups'].browse([group.id for group in portal_groups if group])

        for user in self:
            commands = [(3, group.id) for group in portal_groups]
            selected_group = profile_groups.get(user.car_repair_portal_profile)
            if selected_group:
                commands.append((4, selected_group.id))
            if commands:
                user.groups_id = commands

    @api.depends('share')
    def _compute_car_repair_user_type(self):
        for user in self:
            if user.share:
                user.car_repair_user_type = 'portal'
            else:
                user.car_repair_user_type = 'internal'

    def _inverse_car_repair_user_type(self):
        for user in self:
            target_share = (user.car_repair_user_type == 'portal')
            if user.share != target_share:
                user.share = target_share

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'car_repair_user_type' in vals and 'share' not in vals:
                vals['share'] = (vals['car_repair_user_type'] == 'portal')
        return super().create(vals_list)

    def write(self, vals):
        if 'car_repair_user_type' in vals and 'share' not in vals:
            vals['share'] = (vals['car_repair_user_type'] == 'portal')
        return super().write(vals)
