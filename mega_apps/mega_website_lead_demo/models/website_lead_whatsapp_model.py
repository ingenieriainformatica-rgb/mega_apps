from odoo import fields, models  # type: ignore


class WebsiteLeadWhatsapp(models.Model):
    _name = "website.lead.whatsapp"
    _description = "WhatsApp Leads por Website"
    _order = "sequence, id"

    name = fields.Char(string="Nombre", required=True)
    phone = fields.Char(string="Número WhatsApp", required=True)

    website_id = fields.Many2one(
        "website",
        string="Website",
        required=True,
        ondelete="cascade"
    )

    user_id = fields.Many2one(
        "res.users",
        string="Asesor"
    )

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
