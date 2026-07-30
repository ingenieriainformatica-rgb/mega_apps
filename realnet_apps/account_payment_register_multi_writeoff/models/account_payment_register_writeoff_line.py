# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountPaymentRegisterWriteoffLine(models.TransientModel):
    """
    TransientModel to handle multiple writeoff lines in payment register wizard.
    Each line represents a different writeoff account with its own amount and label.
    Must be TransientModel because it relates to account.payment.register (TransientModel).
    """
    _name = 'account.payment.register.writeoff.line'
    _description = 'Payment Register Writeoff Line'
    _order = 'sequence, id'
    _check_company_auto = True

    # =========================================================================
    # CAMPOS PRINCIPALES
    # =========================================================================

    payment_register_id = fields.Many2one(
        comodel_name='account.payment.register',
        string='Payment Register',
        required=True,
        ondelete='cascade',
        index=True,
        help='Reference to the payment register wizard'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Used to order the writeoff lines'
    )

    account_id = fields.Many2one(
        comodel_name='account.account',
        string='Account',
        required=True,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        help='Account where the writeoff will be posted'
    )

    label = fields.Char(
        string='Label',
        required=True,
        default='Write-Off',
        help='Label for the journal item'
    )

    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id',
        help='Amount of the writeoff (always positive)'
    )

    # =========================================================================
    # CAMPOS RELACIONADOS
    # =========================================================================

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        related='payment_register_id.company_id',
        store=True,
        index=True
    )

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        related='payment_register_id.currency_id',
        store=True
    )

    # =========================================================================
    # VALIDACIONES
    # =========================================================================

    @api.constrains('amount', 'currency_id')
    def _check_amount_not_zero(self):
        """Validate that the amount is not zero."""
        for line in self:
            if line.currency_id and line.currency_id.is_zero(line.amount):
                raise ValidationError(_(
                    "The amount of writeoff line '%(label)s' cannot be zero.",
                    label=line.label
                ))

    # =========================================================================
    # ONCHANGE METHODS
    # =========================================================================

    @api.onchange('account_id')
    def _onchange_account_id(self):
        """Suggest a label based on the account name when account changes."""
        if self.account_id and (not self.label or self.label == 'Write-Off'):
            self.label = self.account_id.name or 'Write-Off'

    # =========================================================================
    # MÉTODOS DE NOMBRE Y DISPLAY
    # =========================================================================

    def name_get(self):
        """Display name for the writeoff line."""
        result = []
        for line in self:
            name = f"{line.label} - {line.amount} ({line.account_id.code})"
            result.append((line.id, name))
        return result
