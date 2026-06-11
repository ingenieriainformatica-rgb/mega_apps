from odoo import _, models  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore


SKIP_LOST_STAGE_VALIDATION = "skip_lost_stage_validation"


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def _is_fold_lost_stage(self, stage):
        """Folded CRM stage that is not the standard won stage."""
        return bool(stage and stage.fold and not stage.is_won)

    def _check_fold_lost_stage_write(self, vals):
        if self.env.context.get(SKIP_LOST_STAGE_VALIDATION):
            return

        if "stage_id" not in vals or not vals.get("stage_id"):
            return

        target_stage = self.env["crm.stage"].browse(vals["stage_id"]).exists()
        if self._is_fold_lost_stage(target_stage):
            raise ValidationError(
                _(
                    "Para mover esta oportunidad a una etapa final/rechazada, "
                    "primero debes indicar el motivo de pérdida y la nota de cierre."
                )
            )

    def write(self, vals):
        self._check_fold_lost_stage_write(vals)
        return super().write(vals)

    def action_open_lost_stage_reason_wizard(self, target_stage_id):
        self.ensure_one()
        target_stage = self.env["crm.stage"].browse(target_stage_id).exists()

        if not self._is_fold_lost_stage(target_stage):
            return False

        return {
            "name": _("Cerrar oportunidad como perdida"),
            "type": "ir.actions.act_window",
            "res_model": "mega.crm.lost.stage.reason.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "default_lead_id": self.id,
                "default_target_stage_id": target_stage.id,
                "dialog_size": "medium",
            },
        }
