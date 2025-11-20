# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Website(models.Model):
    _inherit = 'website'

    fab_phone = fields.Char(string='FAB Phone Number')
    fab_whatsapp = fields.Char(string='FAB WhatsApp Number')


class WebsitePage(models.Model):
    _inherit = 'website.page'

    fab_phone = fields.Char(string='FAB Phone Number (override)')
    fab_whatsapp = fields.Char(string='FAB WhatsApp Number (override)')

    def get_fab_contacts(self):
        self.ensure_one()
        phone = self.fab_phone or self.website_id.fab_phone
        wa = self.fab_whatsapp or self.website_id.fab_whatsapp
        return {
            'phone': phone,
            'whatsapp': wa,
        }


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # show/edit website defaults from Settings app (related to selected website)
    fab_phone = fields.Char(related='website_id.fab_phone', readonly=False)
    fab_whatsapp = fields.Char(related='website_id.fab_whatsapp', readonly=False)


class PageProperties(models.TransientModel):
    _inherit = 'website.page.properties'

    # allow editing per-page values in the Page Properties dialog
    fab_phone = fields.Char(related='target_model_id.fab_phone', readonly=False)
    fab_whatsapp = fields.Char(related='target_model_id.fab_whatsapp', readonly=False)
