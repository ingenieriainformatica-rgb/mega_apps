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


class SlotDetails(models.Model):
    """Details for Slot"""
    _name = 'slot.details'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Details about slot'

    code = fields.Char(string='Code', tracking=True, required=True,
                       help='Unique identifier for slot')
    name = fields.Char(string='Name', required=True,
                       help='Name of the slot')
    slot_type_id = fields.Many2one('slot.type', string='Slot Type',
                                   tracking=True, required=True,
                                   help='Type of the slot')
    site_id = fields.Many2one(
        'parking.site',
        string='Parking Site',
        required=True,
        tracking=True,
        index=True,
        help='Parking site where this slot is located'
    )
    is_available = fields.Boolean(
        string='Available',
        compute='_compute_is_available',
        store=True,
        help='True if slot has no active parking entry in check_in state'
    )
    current_parking_entry_id = fields.Many2one(
        'parking.entry',
        string='Current Parking Entry',
        compute='_compute_current_parking_entry',
        store=True,
        help='Current active parking entry for this slot (if any)'
    )

    @api.depends('name')  # Simple trigger - we'll update via parking.entry model
    def _compute_is_available(self):
        """Compute if slot is available (no active parking entry)"""
        for slot in self:
            # Check if there's any parking entry in 'check_in' state for this slot
            active_entries = self.env['parking.entry'].search([
                ('slot_id', '=', slot.id),
                ('state', '=', 'check_in')
            ], limit=1)
            slot.is_available = not bool(active_entries)

    @api.depends('name')  # Simple trigger - we'll update via parking.entry model
    def _compute_current_parking_entry(self):
        """Compute current active parking entry for this slot"""
        for slot in self:
            # Find the current active parking entry (in check_in state)
            active_entry = self.env['parking.entry'].search([
                ('slot_id', '=', slot.id),
                ('state', '=', 'check_in')
            ], limit=1)
            slot.current_parking_entry_id = active_entry.id if active_entry else False

    def refresh_availability(self):
        """Force refresh of computed fields - called from parking.entry"""
        self._compute_is_available()
        self._compute_current_parking_entry()
