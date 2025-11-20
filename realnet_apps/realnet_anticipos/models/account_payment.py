# -*- coding: utf-8 -*-
"""Modify standalone payments to use advances accounts for customers and suppliers.

Customer logic:
- Standalone inbound customer payments (no invoices, not internal transfer) use anticipos_customer_account_id.

Supplier logic:
- Standalone outbound supplier payments (no bills, not internal transfer) use anticipos_supplier_account_id.

A payment IS NOT an advance (and must use normal receivable/payable) when:
- It is created from the Register Payment wizard on one or more invoices/bills (context active_model == account.move with invoice moves), OR
- It already has invoice_ids (link to invoices/bills).

Previous detection based only on context active_model == 'account.move' was insufficient in some flows, causing
payments created from invoices to be treated as advances. We strengthen detection.
"""
from odoo import models, _, fields, api
from odoo.exceptions import UserError
import logging
__logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    realnet_invoice_origin = fields.Boolean(string='(Realnet) Invoice Payment Origin', copy=False, readonly=True)

    # --- Helpers ---
    def _is_internal_transfer_realnet(self):
        self.ensure_one()
        return bool(getattr(self, 'is_internal_transfer', False))

    def _realnet_is_from_invoice_flow(self):
        """Detection now also considers context flag skip_invoice_sync used by Register Payment wizard."""
        self.ensure_one()
        if self.realnet_invoice_origin:
            return True
        if getattr(self, 'invoice_ids', False) and self.invoice_ids:
            return True
        # During create (before reconciliation) wizard sets context skip_invoice_sync
        ctx = self.env.context
        if ctx.get('skip_invoice_sync') and self.partner_id:
            partner = self.partner_id.commercial_partner_id
            company = self.company_id
            ar = partner.with_company(company).property_account_receivable_id
            ap = partner.with_company(company).property_account_payable_id
            dest_acc = getattr(self, 'destination_account_id', False)
            if dest_acc and dest_acc.id in (ar.id if ar else 0, ap.id if ap else 0):
                return True
        return False

    @api.model_create_multi
    def create(self, vals_list):
        ctx = self.env.context
        valid_types = {'out_invoice','out_refund','in_invoice','in_refund'}
        # Flag payments coming explicitly from Register Payment wizard (context skip_invoice_sync) or with active_model account.move
        for vals in vals_list:
            if not vals.get('partner_id'):
                continue
            mark = False
            if ctx.get('active_model') == 'account.move' and ctx.get('active_ids'):
                moves = self.env['account.move'].browse(ctx['active_ids']).exists()
                if moves and all(m.move_type in valid_types for m in moves):
                    mark = True
            if not mark and ctx.get('skip_invoice_sync'):
                # Heuristic: destination_account_id equals partner AR/AP
                partner = self.env['res.partner'].browse(vals['partner_id']).commercial_partner_id
                company = self.env['res.company'].browse(vals.get('company_id')) if vals.get('company_id') else self.env.company
                ar = partner.with_company(company).property_account_receivable_id
                ap = partner.with_company(company).property_account_payable_id
                dest_id = vals.get('destination_account_id')
                if dest_id and dest_id in filter(None, [ar.id if ar else False, ap.id if ap else False]):
                    mark = True
            if mark:
                vals['realnet_invoice_origin'] = True
        return super().create(vals_list)

    def _should_use_customer_advances(self):
        self.ensure_one()
        return (
            self.partner_type == 'customer'
            and self.payment_type == 'inbound'
            and not self._realnet_is_from_invoice_flow()
            and not self._is_internal_transfer_realnet()
            and self.company_id.anticipos_customer_account_id
        )

    def _should_use_supplier_advances(self):
        self.ensure_one()
        return (
            self.partner_type == 'supplier'
            and self.payment_type == 'outbound'
            and not self._realnet_is_from_invoice_flow()
            and not self._is_internal_transfer_realnet()
            and self.company_id.anticipos_supplier_account_id
        )

    # --- Hook ---
    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=False):
        line_vals_list = super()._prepare_move_line_default_vals(write_off_line_vals, force_balance)
        for payment in self:
            if payment._should_use_customer_advances():
                anticipos_acc = payment.company_id.anticipos_customer_account_id
                if not anticipos_acc:
                    raise UserError(_("Configure la 'Cuenta de Anticipos de Clientes' en Contabilidad > Configuración > Ajustes."))
                for lv in line_vals_list:
                    if lv.get('partner_id') == payment.partner_id.id and lv.get('credit', 0.0) > 0:
                        lv['account_id'] = anticipos_acc.id
            elif payment._should_use_supplier_advances():
                anticipos_acc = payment.company_id.anticipos_supplier_account_id
                if not anticipos_acc:
                    raise UserError(_("Configure la 'Cuenta de Anticipos a Proveedores' en Contabilidad > Configuración > Ajustes."))
                for lv in line_vals_list:
                    if lv.get('partner_id') == payment.partner_id.id and lv.get('debit', 0.0) > 0:
                        lv['account_id'] = anticipos_acc.id
        return line_vals_list
