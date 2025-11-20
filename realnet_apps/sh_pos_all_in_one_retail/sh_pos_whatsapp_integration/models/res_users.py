# Part of Softhealer Technologies.
from odoo import fields, models, api

class ResUsers(models.Model):
    _inherit = "res.users"

    sign = fields.Text(string='Signature')

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super(ResUsers,self)._load_pos_data_fields(config_id)
        result.append('sign')
        return result
