from odoo import models, api, _  # type:ignore
from odoo.exceptions import UserError  # type:ignore


class CRMLead(models.Model):
    _inherit = 'crm.lead'

    def unlink(self):
        """Solo usuarios con permiso pueden eliminar leads"""
        if not self.env.user.has_group('mega_website_lead_demo.group_delete_leads_crm'):
            grupo = self.env.ref('mega_website_lead_demo.group_delete_leads_crm', raise_if_not_found=False)
            nombre_grupo = grupo.name if grupo else "Allow deletion of Leads CRM"

            raise UserError(_(
                f'No tienes permiso para eliminar leads.\n'
                f'Grupo: "{nombre_grupo}".\n'
                f'Contacta al administrador del sistema.'
            ))
        return super().unlink()
