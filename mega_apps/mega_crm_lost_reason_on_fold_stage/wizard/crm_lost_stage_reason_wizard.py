from markupsafe import Markup

from odoo import _, fields, models  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from odoo.tools.mail import is_html_empty  # type: ignore

from ..models.crm_lead import SKIP_LOST_STAGE_VALIDATION


class MegaCrmLostStageReasonWizard(models.TransientModel):
    _name = "mega.crm.lost.stage.reason.wizard"
    _description = "Lost Reason Required Before Fold Stage"

    lead_id = fields.Many2one("crm.lead", required=True, ondelete="cascade")
    target_stage_id = fields.Many2one("crm.stage", required=True)
    lost_reason_id = fields.Many2one("crm.lost.reason", string="Motivo de pérdida", required=True)
    lost_feedback = fields.Html("Nota de cierre", sanitize=True, required=True)

    def action_apply(self):
        self.ensure_one()

        if not self.lost_reason_id:
            raise ValidationError(_("Debes indicar el motivo de pérdida."))

        if is_html_empty(self.lost_feedback):
            raise ValidationError(_("Debes indicar la nota de cierre."))

        if not self.lead_id._is_fold_lost_stage(self.target_stage_id):
            raise ValidationError(_("La etapa destino no es una etapa final/rechazada válida."))

        self.lead_id._track_set_log_message(
            Markup('<div style="margin-bottom: 4px;"><p>%s:</p>%s<br /></div>')
            % (_("Lost Comment"), self.lost_feedback)
        )
        self.lead_id.action_set_lost(lost_reason_id=self.lost_reason_id.id)
        self.lead_id.with_context(**{SKIP_LOST_STAGE_VALIDATION: True}).write(
            {"stage_id": self.target_stage_id.id}
        )
        return {"type": "ir.actions.act_window_close"}
