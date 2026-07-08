# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class PartnerMergeDetectWizard(models.TransientModel):
    _name = "partner.merge.detect.wizard"
    _description = "Detectar contactos duplicados para fusion"

    run_phase1_vat = fields.Boolean(string="Fase 1: VAT duplicado", default=True)
    run_phase2_name = fields.Boolean(string="Fase 2: Nombre igual, VAT parcial", default=True)
    result_message = fields.Text(readonly=True)

    def action_detect(self):
        self.ensure_one()
        if not self.run_phase1_vat and not self.run_phase2_name:
            raise UserError(_("Seleccione al menos una fase de deteccion."))

        summary = self.env["partner.merge.proposal"].run_detection(
            run_phase1=self.run_phase1_vat,
            run_phase2=self.run_phase2_name,
        )
        self.result_message = "\n".join([
            _("Propuestas nuevas creadas: %s") % summary["created"],
            _("Omitidas (sin duplicados reales tras revisar jerarquia): %s") % summary["skipped_no_duplicates"],
            _("Omitidas (ya existia una propuesta con ese mismo grupo): %s") % summary["skipped_already_processed"],
            _("Omitidas por VAT/NIT excluido: %s") % summary["skipped_excluded_vat"],
        ])
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
