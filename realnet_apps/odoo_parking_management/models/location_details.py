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
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models


class LocationDetails(models.Model):
    """Details for a location"""
    _name = 'location.details'
    _description = 'Location Details'

    name = fields.Char(string='Locations', required=True,
                       help='Name of the location')
    
    city = fields.Selection([
        ('medellin', 'Medellín'),
        ('cucuta', 'Cúcuta'),
        ('bogota', 'Bogotá'),
    ], string='City', required=True, 
       help='City where this location is available')
    
    # Keep site_id for backwards compatibility but make it optional
    site_id = fields.Many2one(
        'parking.site',
        string='Reference Site',
        required=False,
        index=True,
        help='Reference parking site (for backwards compatibility)'
    )
