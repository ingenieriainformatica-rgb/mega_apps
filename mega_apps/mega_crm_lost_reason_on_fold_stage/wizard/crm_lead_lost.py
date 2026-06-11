from odoo import _, models  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from odoo.tools.mail import is_html_empty  # type: ignore


class CrmLeadLost(models.TransientModel):
    _inherit = "crm.lead.lost"

    def action_lost_reason_apply(self):
        self.ensure_one()

        if not self.lost_reason_id:
            raise ValidationError(_("Debes indicar el motivo de pérdida."))

        if is_html_empty(self.lost_feedback):
            raise ValidationError(_("Debes indicar la nota de cierre."))

        return super().action_lost_reason_apply()
