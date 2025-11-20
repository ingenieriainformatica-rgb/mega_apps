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


class ParkingSite(models.Model):
    """Model for managing parking sites (sedes)"""
    _name = 'parking.site'
    _description = 'Parking Site'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'city, name'

    name = fields.Char(
        string='Site Name',
        required=True,
        help='Name of the parking site'
    )
    
    city = fields.Selection([
        ('medellin', 'Medellín'),
        ('cucuta', 'Cúcuta'),
        ('bogota', 'Bogotá'),
    ], string='City', required=True, help='City where the site is located')
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help='Company that owns this site'
    )
    
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        help='Analytic account for financial reporting by site'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If unchecked, this site will be hidden'
    )
    
    # Configuration: whether assigning a physical slot is mandatory
    slot_required = fields.Boolean(
        string='Require Slot Assignment',
        default=True,
        help='If enabled, assigning a parking slot (cupo) is mandatory for entries in this site'
    )
    
    # Statistics fields
    parking_entry_count = fields.Integer(
        string='Parking Entries',
        compute='_compute_parking_entry_count',
        help='Number of parking entries for this site'
    )
    
    @api.depends('name')
    def _compute_parking_entry_count(self):
        """Compute the number of parking entries for each site"""
        for site in self:
            site.parking_entry_count = self.env['parking.entry'].search_count([
                ('site_id', '=', site.id)
            ])
    
    @api.constrains('name', 'city', 'company_id')
    def _check_unique_site_per_city_company(self):
        """Ensure site names are unique per city and company"""
        for site in self:
            existing = self.search([
                ('name', '=', site.name),
                ('city', '=', site.city),
                ('company_id', '=', site.company_id.id),
                ('id', '!=', site.id)
            ])
            if existing:
                raise ValidationError(_(
                    'A site with name "%s" already exists in %s for company %s'
                ) % (site.name, dict(self._fields['city'].selection)[site.city], site.company_id.name))

    def name_get(self):
        """Custom name_get to show city and site name"""
        result = []
        for site in self:
            city_name = dict(self._fields['city'].selection)[site.city]
            name = f"{city_name} - {site.name}"
            result.append((site.id, name))
        return result

    def action_view_parking_entries(self):
        """Action to view parking entries for this site"""
        return {
            'name': _('Parking Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'parking.entry',
            'view_mode': 'list,form',
            'domain': [('site_id', '=', self.id)],
            'context': {'default_site_id': self.id},
        }
