# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class FleetDiagnoseAssigntoTechnician(models.TransientModel):
    _name = 'fleet.diagnose.assignto.technician'
    _description = "Fleet diagnose assignto technician"

    user_id = fields.Many2one('res.users', string='Technician', required=True)

    def do_assign_technician(self):
        if self.user_id and self._context.get('active_id'):
            diagnose = self.env['fleet.diagnose'].browse(self._context.get('active_id'))
            diagnose.write({'user_id': self.user_id.id, 'state': 'in_progress'})
            if diagnose.fleet_repair_id:
                diagnose.fleet_repair_id.write({'portal_technician_id': self.user_id.id})
        return {'type': 'ir.actions.act_window_close'}
