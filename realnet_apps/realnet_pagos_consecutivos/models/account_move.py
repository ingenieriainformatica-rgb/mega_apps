from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # Show the CE/CI number from the related payment on the journal entry title when applicable.
    x_ceci_number = fields.Char(
        string="CE/CI Number",
        compute="_compute_x_ceci_number",
        store=False,
        help="Consecutivo CE/CI del pago relacionado (si aplica).",
    )

    def _get_related_payment(self):
        self.ensure_one()
        # Prefer the canonical link from move to payment
        payment = getattr(self, "origin_payment_id", False)
        if payment:
            return payment
        # Fallback: some lines can carry the payment_id
        line_payments = self.line_ids.mapped("payment_id")
        if line_payments:
            return line_payments[0]
        # Last resort: receivable/payable matching links (older flows)
        lines = self.line_ids.filtered(
            lambda l: l.account_id.account_type in ("asset_receivable", "liability_payable")
        )
        payments = (
            lines.mapped("matched_debit_ids.debit_move_id.payment_id")
            | lines.mapped("matched_credit_ids.credit_move_id.payment_id")
        )
        return payments[:1] if payments else False

    @api.depends(
        "origin_payment_id",
        "origin_payment_id.x_ceci_number",
        "line_ids.payment_id",
        "line_ids.payment_id.x_ceci_number",
        "line_ids.matched_debit_ids",
        "line_ids.matched_credit_ids",
    )
    def _compute_x_ceci_number(self):
        for move in self:
            payment = move._get_related_payment()
            move.x_ceci_number = payment.x_ceci_number if payment else False
