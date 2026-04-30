from odoo import fields, models  # type: ignore


class Website(models.Model):
    _inherit = "website"

    lead_whatsapp_ids = fields.One2many(
        "website.lead.whatsapp",
        "website_id",
        string="WhatsApps Leads"
    )
