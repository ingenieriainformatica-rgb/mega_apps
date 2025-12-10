import logging  #type:ignore
from odoo import models, _  #type:ignore
from odoo.exceptions import UserError  #type:ignore

_logger = logging.getLogger(__name__)

STATE_POSTED = "posted"
FIELD_CONCEPTO = "x_studio_concepto"


class AccountMove(models.Model):
    _inherit = "account.move"

    def write(self, vals):

        # _logger.info(f"\n\n Context: {self.env.context} \n\n")

        if FIELD_CONCEPTO in vals:
            locked = self.filtered(lambda m: m.state == STATE_POSTED)
            if locked:
                raise UserError(_("No se puede modificar el campo Concepto en facturas registradas."))
        return super().write(vals)
