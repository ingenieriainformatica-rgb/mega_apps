# Copyright (C) Softhealer Technologies.
# Part of Softhealer Technologies.

from odoo import models, api

class PosSessionInherit(models.Model):
    _inherit = "pos.session"

    @api.model
    def _load_pos_data_models(self, config_id):
        data_models = super()._load_pos_data_models(config_id)
        # UOM feature code 
        data_models += ['product.suggestion','sh.uom.line']
        return data_models

#     def _pos_ui_models_to_load(self):
#         result = super()._pos_ui_models_to_load()
#         if 'product.suggestion' not in result:
#             result.append('product.suggestion')
       
#         return result

#     def _loader_params_product_suggestion(self):
#         return {'search_params': {'domain': [], 'fields': [], 'load': False}}

#     def _get_pos_ui_product_suggestion(self, params):
#         return self.env['product.suggestion'].search_read(**params['search_params'])
    

    
#     def _loader_params_product_product(self):
#         result = super()._loader_params_product_product()
#         result['search_params']['fields'].append('suggestion_line')
#         return result
