# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class PartnerUppercaseWizard(models.TransientModel):
    _name = "partner.uppercase.wizard"
    _description = "Actualizar nombres de contactos a MAYÚSCULA"

    def action_confirm(self):
        self.ensure_one()
        return self.env["res.partner"].action_update_names_uppercase()
