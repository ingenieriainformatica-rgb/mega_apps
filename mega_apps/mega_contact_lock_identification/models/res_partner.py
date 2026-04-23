# -*- coding: utf-8 -*-
from odoo import models  # type: ignore


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _l10n_co_dian_onchange_identification_type(self):
        return
