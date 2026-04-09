import logging
from odoo import models, api, _  #type: ignore
from odoo.exceptions import ValidationError, UserError  #type: ignore

_logger = logging.getLogger(__name__)
MODULE_NAME = 'contacts'


class ResPartner(models.Model):
    _inherit = 'res.partner'


    # -----------------------------------
    # Utils
    # -----------------------------------
    def _is_from_contacts(self):
        params = self.env.context.get('params', {})
        return params.get('action') == MODULE_NAME


    # -----------------------------------
    # CREATE
    # -----------------------------------
    @api.model
    def create(self, vals):
        if self._is_from_contacts():
            vat = (vals.get('vat') or '').strip()
            domain = []
            if vat:
                domain.append(('vat', '=', vat))
                if domain:
                    existing = self.search(domain, limit=1)

                    if existing:
                        raise ValidationError(_(
                            "⚠️ Ya existe un contacto con estos datos:\n\n"
                            "Nombre: %s\n"
                            "Documento: %s"
                        ) % (
                            existing.name,
                            vat
                        ))

        return super().create(vals)

    # -----------------------------------
    # WRITE
    # -----------------------------------
    def write(self, vals):

        if self._is_from_contacts():

            # 👇 evitar romper sistema
            if (
                not self.env.user.has_group('mega_fix_module_contact.group_module_contact')
            ):
                raise UserError(_(
                    "No tienes permisos para editar contactos.\n"
                    "Contacta al administrador.\n"
                    "Grupo requerido: Module contact permissions"
                ))

        return super().write(vals)