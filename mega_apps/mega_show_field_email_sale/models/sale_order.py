import logging
from odoo import api, fields, models  # type: ignore

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    partner_email = fields.Char(
        string='Email',
        help='Correo tomado del cliente al seleccionar el contacto en la cotización.'
    )

    @api.onchange('partner_id')
    def _onchange_partner_id_set_partner_email(self):
        for order in self:
            order.partner_email = order.partner_id.email or False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner_id = vals.get('partner_id')
            if partner_id and not vals.get('partner_email'):
                partner = self.env['res.partner'].browse(partner_id)
                vals['partner_email'] = partner.email or False

        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)

        if 'partner_id' in vals:
            partner_id = vals.get('partner_id')
            if partner_id:
                partner = self.env['res.partner'].browse(partner_id)
                vals['partner_email'] = partner.email or False
            else:
                vals['partner_email'] = False

        return super().write(vals)
