# -*- coding: utf-8 -*-

from odoo import models, _  #type: ignore
from odoo.exceptions import UserError  #type: ignore


class AccountMove(models.Model):
    _inherit = "account.move"

    def unlink(self):
        if self.env.context.get("force_delete_account_documents"):
            return super().unlink()

        protected_moves = self.filtered(lambda move:
            # move.state == "posted"
            # and move.move_type == "entry"
            move.move_type in (
                "entry",
                "out_invoice",
                "out_refund",
                "in_invoice",
                "in_refund",
            )
        )

        if protected_moves and not self.env.user.has_group(
            "mega_account_delete_restriction.group_account_delete_documents"
        ):
            raise UserError(_(
                "No tienes permisos para eliminar asientos contables publicados.\n\n"
                "Esta acción está restringida por control contable. "
                "Solicita autorización a un usuario con permisos especiales.\n\n"
                "Group: Allow deletion of accounting entries and payments"
            ))

        return super().unlink()
