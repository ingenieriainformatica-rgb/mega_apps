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
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    """Extend res.users with parking site management fields"""
    _inherit = 'res.users'

    allowed_parking_site_ids = fields.Many2many(
        'parking.site',
        'rel_user_parking_site',
        'user_id',
        'site_id',
        string='Allowed Parking Sites',
        help='Parking sites this user can access'
    )
    
    default_parking_site_id = fields.Many2one(
        'parking.site',
        string='Default Parking Site',
        help='Default site for parking operations'
    )
    
    @api.constrains('default_parking_site_id', 'allowed_parking_site_ids')
    def _check_default_site_in_allowed(self):
        """Ensure default site is within allowed sites"""
        for user in self:
            if (user.default_parking_site_id and 
                user.default_parking_site_id not in user.allowed_parking_site_ids):
                raise ValidationError(_(
                    'Default parking site must be one of the allowed sites'
                ))
    
    @api.onchange('allowed_parking_site_ids')
    def _onchange_allowed_sites(self):
        """Clear default site if it's no longer in allowed sites"""
        if (self.default_parking_site_id and 
            self.default_parking_site_id not in self.allowed_parking_site_ids):
            self.default_parking_site_id = False
    
    def get_user_parking_sites_domain(self):
        """Get domain for parking sites accessible by current user"""
        if self.env.user.has_group('odoo_parking_management.group_parking_admin'):
            return []  # Admins see all sites
        return [('id', 'in', self.env.user.allowed_parking_site_ids.ids)]
    
    def get_default_parking_site(self):
        """Get default parking site for current user"""
        user = self.env.user
        if user.default_parking_site_id:
            return user.default_parking_site_id
        elif len(user.allowed_parking_site_ids) == 1:
            return user.allowed_parking_site_ids[0]
        return False
