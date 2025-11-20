from odoo import fields, models
from odoo.exceptions import UserError
class SignRequest(models.Model):
    _inherit = 'sign.request'

    x_contract_id = fields.Many2one('x.contract', string="Contrato")

    def action_request_signature(self, template_xml_id=None):
        """Crea una sign.request desde una plantilla (por nombre o xmlid) y la envía al partner."""
        self.ensure_one()
        SignTemplate = self.env['sign.template']

        template = None
        if template_xml_id:
            template = self.env.ref(template_xml_id, raise_if_not_found=False)
        if not template:
            # fallback: busca por nombre (ajusta al tuyo)
            template = SignTemplate.search([('name', '=', 'Contrato de Servicios')], limit=1)
        if not template:
            raise UserError("No se encontró la plantilla de firma.")

        req = self.env['sign.request'].create({
            'template_id': template.id,
            'x_contract_id': self.id,
            'reference': f'{self.display_name}',
            # asigna destinatarios si usas roles de la plantilla
        })

        # Si manejas roles, aquí vinculas el partner del contrato a un rol
        # req.request_item_ids.create({...})

        # Opcional: enviar por correo
        # req._send_signature_request()

        # Abrir la vista de la request
        return {
            'type': 'ir.actions.act_window',
            'name': 'Solicitud de firma',
            'res_model': 'sign.request',
            'view_mode': 'form',
            'res_id': req.id,
            'target': 'current',
        }