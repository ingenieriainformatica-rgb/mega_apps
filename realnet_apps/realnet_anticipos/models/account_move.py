# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Campo técnico para compatibilidad; no lo usamos en la lógica
    realnet_from_invoice = fields.Boolean(
        string='(Technical) From Invoice Wizard',
        default=False,
        copy=False,
        readonly=True,
        index=True,
    )
class AccountMove(models.Model):
    _inherit = 'account.move'

    def _realnet_get_misc_journal(self):
        """Devuelve el diario para la reclasificación:
           1) company.realnet_reclass_journal_id si está configurado y activo
           2) de lo contrario, el primer 'general' activo con cuenta por defecto (si la tiene) o el primero activo.
        """
        self.ensure_one()
        company = self.company_id
        journal = getattr(company, 'realnet_reclass_journal_id', False)
        if journal and journal.active and journal.type == 'general':
            return journal

        journals = self.env['account.journal'].search([
            ('company_id', '=', company.id),
            ('type', '=', 'general'),
            ('active', '=', True),
        ])
        for j in journals:
            if j.default_account_id:
                return j
        if journals:
            return journals[0]
        raise UserError(_("Debe existir un Diario Misceláneo (tipo 'general') en la compañía %s.") % company.display_name)

    def action_post(self):
        res = super().action_post()
        for inv in self.filtered(lambda m: m.state == 'posted'):
            try:
                if inv.move_type == 'out_invoice':
                    inv._realnet_apply_customer_advances_single()
                elif inv.move_type == 'in_invoice':
                    inv._realnet_apply_supplier_advances_single()
            except Exception as e:
                _logger.exception("REALNET Anticipos: error aplicando anticipo en %s: %s", inv.name or inv.id, e)
        return res

    def _realnet_apply_customer_advances_single(self):
        self.ensure_one()
        inv = self
        company = inv.company_id
        partner = inv.partner_id.commercial_partner_id
        adv_acc = company.anticipos_customer_account_id

        if not adv_acc:
            _logger.info("REALNET Anticipos: sin cuenta de anticipos configurada en %s. Skip.", company.display_name)
            return
        if not adv_acc.reconcile:
            raise UserError(_("La cuenta de anticipos de clientes (%s) debe permitir conciliación.") % adv_acc.display_name)

        receivable_account = inv.partner_id.with_company(company).property_account_receivable_id
        if not receivable_account:
            _logger.info("REALNET Anticipos: partner %s sin CxC configurada en %s.", partner.display_name, company.display_name)
            return

        recv_line = inv.line_ids.filtered(
            lambda l: l.company_id == company and l.account_id.id == receivable_account.id and l.debit > 0
        )[:1]
        if not recv_line:
            _logger.info("REALNET Anticipos: no se encontró línea CxC (%s) en factura %s.", receivable_account.display_name, inv.name)
            return

        adv_lines = self.env['account.move.line'].search([
            ('company_id', '=', company.id),
            ('partner_id', '=', partner.id),
            ('account_id', '=', adv_acc.id),
            ('reconciled', '=', False),
        ], order='date,id')

        if not adv_lines:
            _logger.info("REALNET Anticipos: %s no tiene anticipos pendientes en %s.", partner.display_name, adv_acc.display_name)
            return

        anticipo_disponible = sum(max(0.0, -l.amount_residual if l.amount_residual < 0 else l.amount_residual) for l in adv_lines)
        if anticipo_disponible <= 0.0 or inv.amount_residual <= 0.0:
            _logger.info("REALNET Anticipos: nada por aplicar (disponible=%.2f, residual=%.2f).", anticipo_disponible, inv.amount_residual)
            return

        to_apply = min(inv.amount_residual, anticipo_disponible)

        misc_journal = inv._realnet_get_misc_journal()
        ref = _("Reclasificación anticipo → %s") % (inv.name or inv.ref or inv.id)
        date = inv.invoice_date or fields.Date.context_today(self)

        move_vals = {
            'move_type': 'entry',
            'journal_id': misc_journal.id,
            'company_id': company.id,
            'date': date,
            'ref': ref,
            'line_ids': [
                (0, 0, {
                    'name': ref,
                    'partner_id': partner.id,
                    'company_id': company.id,
                    'account_id': adv_acc.id,
                    'debit': to_apply,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': ref,
                    'partner_id': partner.id,
                    'company_id': company.id,
                    'account_id': receivable_account.id,
                    'debit': 0.0,
                    'credit': to_apply,
                }),
            ],
        }
        reclass_move = self.env['account.move'].with_context(default_move_type='entry').create(move_vals)
        reclass_move.action_post()
        _logger.info("REALNET Anticipos: creado %s por %.2f para %s.", reclass_move.name, to_apply, inv.name)

    # ---------------- PROVEEDORES ----------------
    def _realnet_apply_supplier_advances_single(self):
        """Reclasifica anticipo (ACTIVO) -> CxP y deja el débito en CxP como pendiente (sin conciliar)."""
        self.ensure_one()
        inv = self
        if inv.move_type != 'in_invoice':
            return

        company = inv.company_id
        partner = inv.partner_id.commercial_partner_id
        adv_acc = company.anticipos_supplier_account_id

        if not adv_acc:
            _logger.info("REALNET Anticipos (PROV): sin cuenta de anticipos de proveedores configurada en %s.", company.display_name)
            return
        if not adv_acc.reconcile:
            raise UserError(_("La cuenta de anticipos a proveedores (%s) debe permitir conciliación.") % adv_acc.display_name)

        payable_account = inv.partner_id.with_company(company).property_account_payable_id
        if not payable_account:
            _logger.info("REALNET Anticipos (PROV): partner %s sin CxP configurada en %s.", partner.display_name, company.display_name)
            return

        # CxP de la factura: crédito en la cuenta CxP del partner
        pay_line = inv.line_ids.filtered(
            lambda l: l.company_id == company and l.account_id.id == payable_account.id and l.credit > 0
        )[:1]
        if not pay_line:
            _logger.info("REALNET Anticipos (PROV): no se encontró línea CxP (%s) en factura %s.", payable_account.display_name, inv.name)
            return

        # Anticipos a proveedores (activo) no conciliados
        adv_lines = self.env['account.move.line'].search([
            ('company_id', '=', company.id),
            ('partner_id', '=', partner.id),
            ('account_id', '=', adv_acc.id),
            ('reconciled', '=', False),
        ], order='date,id')
        if not adv_lines:
            _logger.info("REALNET Anticipos (PROV): %s no tiene anticipos pendientes en %s.", partner.display_name, adv_acc.display_name)
            return

        anticipo_disponible = sum(max(0.0, -l.amount_residual if l.amount_residual < 0 else l.amount_residual) for l in adv_lines)
        if anticipo_disponible <= 0.0 or inv.amount_residual <= 0.0:
            _logger.info("REALNET Anticipos (PROV): nada por aplicar (disponible=%.2f, residual=%.2f).", anticipo_disponible, inv.amount_residual)
            return

        to_apply = min(inv.amount_residual, anticipo_disponible)

        misc_journal = inv._realnet_get_misc_journal()
        ref = _("Reclasificación anticipo proveedor → %s") % (inv.name or inv.ref or inv.id)
        date = inv.invoice_date or fields.Date.context_today(self)

        move_vals = {
            'move_type': 'entry',
            'journal_id': misc_journal.id,
            'company_id': company.id,
            'date': date,
            'ref': ref,
            'line_ids': [
                # HABER: Anticipos a proveedores (reduce el activo por el monto aplicado)
                (0, 0, {
                    'name': ref,
                    'partner_id': partner.id,
                    'company_id': company.id,
                    'account_id': adv_acc.id,
                    'debit': 0.0,
                    'credit': to_apply,
                }),
                # DEBE: CxP del partner -> queda como "pago/crédito pendiente" para aplicar manualmente
                (0, 0, {
                    'name': ref,
                    'partner_id': partner.id,
                    'company_id': company.id,
                    'account_id': payable_account.id,
                    'debit': to_apply,
                    'credit': 0.0,
                }),
            ],
        }
        reclass_move = self.env['account.move'].with_context(default_move_type='entry').create(move_vals)
        reclass_move.action_post()
        _logger.info("REALNET Anticipos (PROV): creado %s por %.2f para %s.", reclass_move.name, to_apply, inv.name)
        _logger.info("REALNET Anticipos (PROV): conciliación NO automática (queda pendiente en CxP).")
