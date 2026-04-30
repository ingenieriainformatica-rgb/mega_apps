# -*- coding: utf-8 -*-

from odoo import models, _  #type: ignore
from odoo.exceptions import UserError  #type: ignore


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def unlink(self):
        if self.env.context.get("force_delete_account_documents"):
            return super().unlink()

        protected_payments = self.filtered(lambda payment:
            payment.state in ("posted", "paid", "in_process")
        )

        if protected_payments and not self.env.user.has_group(
            "mega_account_delete_restriction.group_account_delete_documents"
        ):
            raise UserError(_(
                "No tienes permisos para eliminar pagos confirmados.\n\n"
                "Esta acción está restringida por control contable. "
                "Solicita autorización a un usuario con permisos especiales.\n\n"
                "Group: Allow deletion of accounting entries and payments"
            ))

        return super().unlink()
