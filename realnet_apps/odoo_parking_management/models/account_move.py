# -*- coding: utf-8 -*-
from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _update_parking_entries_payment_status(self):
        """Método para actualizar el estado de parking entries cuando las facturas se paguen"""
        # Buscar parking entries que tengan facturas pagadas pero que no estén marcadas como pagadas
        parking_entries = self.env['parking.entry'].search([
            ('invoice_id.payment_state', '=', 'paid'),
            ('state', '!=', 'payment')
        ])
        
        for entry in parking_entries:
            entry.update_payment_status()

    def write(self, vals):
        """Override write to detect payment state changes"""
        result = super(AccountMove, self).write(vals)
        
        # Si se actualiza el payment_state, verificar parking entries relacionados
        if 'payment_state' in vals or any(key.startswith('line_ids') for key in vals.keys()):
            # Buscar parking entries relacionados con estas facturas
            parking_entries = self.env['parking.entry'].search([
                ('invoice_id', 'in', self.ids)
            ])
            
            for entry in parking_entries:
                if entry.invoice_id.payment_state == 'paid' and entry.state != 'payment':
                    entry.update_payment_status()
        
        return result


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    def _prepare_analytic_distribution_for_parking_site(self, site_id):
        """Prepare analytic distribution for parking site"""
        if not site_id:
            return {}
        
        site = self.env['parking.site'].browse(site_id)
        if site.analytic_account_id:
            return {str(site.analytic_account_id.id): 100.0}
        
        return {}
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set analytic distribution for parking invoices"""
        for vals in vals_list:
            # Check if this is a parking invoice line
            if vals.get('move_id'):
                move = self.env['account.move'].browse(vals['move_id'])
                # Find related parking entry
                parking_entry = self.env['parking.entry'].search([
                    ('invoice_id', '=', move.id)
                ], limit=1)
                
                if parking_entry and parking_entry.site_id and parking_entry.site_id.analytic_account_id:
                    # Set analytic distribution for this site
                    analytic_distribution = self._prepare_analytic_distribution_for_parking_site(
                        parking_entry.site_id.id
                    )
                    if analytic_distribution and not vals.get('analytic_distribution'):
                        vals['analytic_distribution'] = analytic_distribution
        
        return super().create(vals_list)
