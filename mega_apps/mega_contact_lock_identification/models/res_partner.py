# -*- coding: utf-8 -*-
import logging
from odoo import models, api  # type: ignore

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.onchange("company_type", "is_company")
    def _onchange_set_identification_type_for_person(self):
        identification_model = self.env["l10n_latam.identification.type"]

        for rec in self:
            is_person = rec.company_type == "person" or not rec.is_company
            current_name = (rec.l10n_latam_identification_type_id.name or "").strip().lower()
            if is_person:
                if "cédula" in current_name:
                    continue

                identification_type = identification_model.search([
                    ("name", "ilike", "cédula de ciudadanía")
                ], limit=1)
            else:
                if "nit" in current_name:
                    continue

                identification_type = identification_model.search([
                    ("name", "ilike", "nit")
                ], limit=1)

            if identification_type:
                rec.l10n_latam_identification_type_id = identification_type

    # def _l10n_co_dian_onchange_identification_type(self):
    #     return
