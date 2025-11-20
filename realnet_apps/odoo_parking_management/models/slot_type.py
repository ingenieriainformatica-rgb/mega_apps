# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#   This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models


class SlotType(models.Model):
    """Details of slot type"""
    _name = 'slot.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'vehicle_type'
    _description = 'Slot Type'

    vehicle_type = fields.Char(string='Name', required=True,
                               tracking=True, help='Name of vehicle')
    code = fields.Char(string='Code', tracking=True,
                       help='Unique identifier for vehicle')
    allowed_park_duration = fields.Float(string='Allowed Parking Time',
                                         help='Time allowed for the vehicle')

    @api.model
    def get_or_create_defaults(self):
        """Ensure default slot types exist and return their ids.

        Returns a dict mapping keys 'auto', 'moto', 'other' to record dicts
        with 'id' and 'display_name'.
        """
        mapping = {
            'auto': {'vehicle_type': 'Automovil', 'code': 'AUTO'},
            'moto': {'vehicle_type': 'Moto', 'code': 'MOTO'},
            'other': {'vehicle_type': 'Otro', 'code': 'OTHER'},
        }
        res = {}
        for key, vals in mapping.items():
            rec = self.search([('code', '=', vals['code'])], limit=1)
            if not rec:
                # fallback on name in case code is not set in DB
                rec = self.search([('vehicle_type', 'ilike', vals['vehicle_type'])], limit=1)
            if not rec:
                rec = self.create(vals)
            res[key] = {'id': rec.id, 'display_name': rec.display_name}
        return res
