import re
from odoo import models, api, _  #type: ignore
from odoo.exceptions import ValidationError, UserError  #type: ignore


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _normalize_vat_digits(self, vat):
        return re.sub(r'\D', '', vat or '')

    def _find_duplicate_vat(self, vat, exclude_ids=None):
        vat_normalized = self._normalize_vat_digits(vat)

        if not vat_normalized:
            return self.browse()

        domain = [('vat', '!=', False)]

        if exclude_ids:
            domain.append(('id', 'not in', exclude_ids))

        partners = self.search(domain)

        for partner in partners:
            partner_vat_normalized = self._normalize_vat_digits(partner.vat)

            if partner_vat_normalized == vat_normalized:
                return partner

        return self.browse()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vat = vals.get('vat')

            if vat:
                duplicate = self._find_duplicate_vat(vat)

                if duplicate:
                    raise ValidationError(_(
                        "⚠️ No se puede crear el contacto.\n\n"
                        "Ya existe un contacto con ese NIT/Cédula:\n\n"
                        "Contacto existente: %s\n"
                        "Documento guardado: %s\n"
                        "Documento ingresado: %s"
                    ) % (
                        duplicate.display_name,
                        duplicate.vat,
                        vat,
                    ))

        return super().create(vals_list)

    # -----------------------------------
    # WRITE
    # -----------------------------------
    def write(self, vals):
        if 'vat' in vals:

            if not self.env.user.has_group('mega_fix_module_contact.group_module_contact'):
                raise UserError(_(
                    "No tienes permisos para editar contactos.\n"
                    "Contacta al administrador.\n"
                    "Grupo requerido: Module contact permissions"
                ))

            vat = vals.get('vat')

            if vat:
                for partner in self:
                    duplicate = self._find_duplicate_vat(
                        vat,
                        exclude_ids=[partner.id]
                    )

                    if duplicate:
                        raise ValidationError(_(
                            "⚠️ No se puede guardar el contacto.\n\n"
                            "Ya existe otro contacto con ese NIT/Cédula:\n\n"
                            "Contacto existente: %s\n"
                            "Documento guardado: %s\n"
                            "Documento ingresado: %s"
                        ) % (
                            duplicate.display_name,
                            duplicate.vat,
                            vat,
                        ))

        return super().write(vals)
