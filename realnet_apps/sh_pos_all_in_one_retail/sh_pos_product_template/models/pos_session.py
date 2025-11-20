# Copyright (C) Softhealer Technologies.
# Part of Softhealer Technologies.

from odoo import models, api


class PosSessionInherit(models.Model):
    _inherit = "pos.session"

    # pos.product.template
    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()

        if "pos.product.template" not in result:
            result.append("pos.product.template")

        if "pos.product.template.line" not in result:
            result.append("pos.product.template.line")

        return result
    @api.model
    def _load_pos_data_models(self, config_id):
        data_models = super()._load_pos_data_models(config_id)
        data_models += ['pos.product.template', 'pos.product.template.line']
        return data_models