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


class AccountMove(models.Model):
    """Extend account.move to support monthly parking invoices"""
    _inherit = 'account.move'

    # Monthly parking fields
    monthly_contract_id = fields.Many2one(
        'parking.monthly.contract',
        string='Monthly Contract',
        help='Monthly parking contract for this invoice'
    )
    parking_period_key = fields.Char(
        string='Parking Period Key',
        help='Unique key for monthly parking period (contract_id-site_id-partner_id-company_id-year-month)'
    )
    parking_billing_period = fields.Char(
        string='Billing Period',
        help='Billing period in YYYY-MM format'
    )
    parking_site_id = fields.Many2one(
        'parking.site',
        string='Parking Site',
        help='Parking site for monthly invoice'
    )
    is_monthly_parking_invoice = fields.Boolean(
        string='Is Monthly Parking Invoice',
        compute='_compute_is_monthly_parking_invoice',
        store=True,
        help='True if this is a monthly parking invoice'
    )

    # Billing mode from contract (for invoice uniqueness)
    billing_mode = fields.Selection([
        ('postpaid', 'Postpaid'),
        ('prepaid', 'Prepaid')
    ], string='Billing Mode', related='monthly_contract_id.billing_mode', store=True,
       help='Billing mode from the related contract')

    @api.depends('monthly_contract_id')
    def _compute_is_monthly_parking_invoice(self):
        """Compute if this is a monthly parking invoice"""
        for move in self:
            move.is_monthly_parking_invoice = bool(move.monthly_contract_id)

    @api.constrains('monthly_contract_id', 'parking_site_id', 'partner_id', 'parking_billing_period', 'billing_mode')
    def _check_unique_monthly_invoice(self):
        """Ensure only one invoice per contract+period+billing_mode"""
        for move in self:
            if move.monthly_contract_id and move.parking_billing_period and move.billing_mode:
                existing = self.search([
                    ('monthly_contract_id', '=', move.monthly_contract_id.id),
                    ('parking_site_id', '=', move.parking_site_id.id),
                    ('partner_id', '=', move.partner_id.id),
                    ('parking_billing_period', '=', move.parking_billing_period),
                    ('billing_mode', '=', move.billing_mode),
                    ('id', '!=', move.id),
                    ('state', '!=', 'cancel')
                ])
                if existing:
                    raise ValidationError(_(
                        'An invoice already exists for contract "%s" in period %s (%s mode). '
                        'Only one invoice per contract per period per billing mode is allowed.'
                    ) % (move.monthly_contract_id.name, move.parking_billing_period, move.billing_mode))

    def action_view_contract(self):
        """View the related monthly contract"""
        if self.monthly_contract_id:
            return {
                'name': _('Monthly Contract'),
                'type': 'ir.actions.act_window',
                'res_model': 'parking.monthly.contract',
                'res_id': self.monthly_contract_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def action_view_parking_entries(self):
        """View parking entries included in this monthly invoice"""
        if self.monthly_contract_id:
            return {
                'name': _('Parking Entries'),
                'type': 'ir.actions.act_window',
                'res_model': 'parking.entry',
                'view_mode': 'list,form',
                'domain': [('monthly_invoice_id', '=', self.id)],
            }
