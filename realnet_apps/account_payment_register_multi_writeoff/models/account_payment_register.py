# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountPaymentRegister(models.TransientModel):
    """
    Extend payment register wizard to support multiple writeoff lines.
    Replaces the single writeoff field with a One2many for multiple lines.
    """
    _inherit = 'account.payment.register'

    # =========================================================================
    # CAMPOS
    # =========================================================================

    writeoff_line_ids = fields.One2many(
        comodel_name='account.payment.register.writeoff.line',
        inverse_name='payment_register_id',
        string='Writeoff Lines',
        copy=False,
    )

    writeoff_lines_total = fields.Monetary(
        string='Writeoff Lines Total',
        compute='_compute_writeoff_lines_total',
        currency_field='currency_id',
    )

    writeoff_lines_total_difference = fields.Monetary(
        string='Writeoff Lines Total Difference',
        compute='_compute_writeoff_lines_total_difference',
        currency_field='currency_id',
    )

    # =========================================================================
    # COMPUTE
    # =========================================================================

    @api.depends('writeoff_line_ids.amount')
    def _compute_writeoff_lines_total(self):
        """Calculate the total sum of writeoff lines."""
        for wizard in self:
            wizard.writeoff_lines_total = sum(wizard.writeoff_line_ids.mapped('amount'))

    @api.depends('writeoff_lines_total', 'payment_difference')
    def _compute_writeoff_lines_total_difference(self):
        for wizard in self:
            wizard.writeoff_lines_total_difference = wizard.writeoff_lines_total - abs(wizard.payment_difference)

    # =========================================================================
    # VALIDACIONES
    # =========================================================================

    @api.constrains('writeoff_line_ids', 'payment_difference', 'payment_difference_handling')
    def _check_writeoff_lines_total(self):
        """
        Validate that the sum of writeoff_line_ids equals the payment_difference.
        """
        for wizard in self:
            if not wizard.show_payment_difference:
                continue

            if wizard.payment_difference_handling != 'reconcile':
                continue

            if not wizard.writeoff_line_ids:
                continue

            total_writeoff = wizard.writeoff_lines_total
            abs_payment_difference = abs(wizard.payment_difference)
            difference = abs_payment_difference - total_writeoff

            if not wizard.currency_id.is_zero(difference):
                raise ValidationError(_(
                    "The sum of writeoff lines (%(total)s) must equal the payment difference (%(diff)s). Current difference: %(current)s",
                    total=wizard.currency_id.format(total_writeoff),
                    diff=wizard.currency_id.format(abs_payment_difference),
                    current=wizard.currency_id.format(abs(difference)),
                ))

    # =========================================================================
    # OVERRIDE: CREACIÓN DE VALORES DEL PAGO
    # =========================================================================

    def _create_payment_vals_from_wizard(self, batch_result):
        """
        Override to build write_off_line_vals from multiple writeoff lines.
        Odoo handles the rest automatically.
        """
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)

        # Si hay líneas de writeoff definidas, usarlas
        if self.writeoff_line_ids and self.payment_difference_handling == 'reconcile':
            # Limpiar writeoff simple que pudiera existir
            payment_vals['write_off_line_vals'] = []

            # Construir lista desde las líneas
            for line in self.writeoff_line_ids:
                # Determinar signo según tipo de pago
                if self.payment_type == 'inbound':
                    write_off_amount_currency = line.amount
                else:
                    write_off_amount_currency = -line.amount

                # Formato estándar de Odoo
                line_vals = {
                    'name': line.label,
                    'account_id': line.account_id.id,
                    'partner_id': self.partner_id.id,
                    'currency_id': self.currency_id.id,
                    'amount_currency': write_off_amount_currency,
                    'balance': self.currency_id._convert(
                        write_off_amount_currency,
                        self.company_id.currency_id,
                        self.company_id,
                        self.payment_date
                    ),
                }

                payment_vals['write_off_line_vals'].append(line_vals)

        return payment_vals
