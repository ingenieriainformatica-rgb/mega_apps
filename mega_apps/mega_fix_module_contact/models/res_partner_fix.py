import re
from odoo import models, api, _  # type: ignore
from odoo.exceptions import ValidationError, UserError  # type: ignore


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ============================================
    # MÉTODOS PRIVADOS
    # ============================================

    def _normalize_vat_digits(self, vat):
        """Limpia el VAT dejando solo dígitos"""
        return re.sub(r'\D', '', vat or '')

    def _find_duplicate_vat(self, vat, exclude_ids=None):
        """Busca si ya existe otro partner con el mismo VAT normalizado"""
        vat_normalized = self._normalize_vat_digits(vat)

        if not vat_normalized:
            return self.browse()

        domain = [('vat', '=ilike', vat_normalized)]

        if exclude_ids:
            domain.append(('id', 'not in', exclude_ids))

        return self.search(domain, limit=1)

    def _build_duplicate_error(self, duplicate, vat):
        """Construye el mensaje de error para VAT duplicado"""
        return ValidationError(_(
            "⚠️ No se puede guardar el contacto.\n\n"
            "Ya existe otro contacto con ese NIT/Cédula:\n\n"
            "• Contacto existente: %(name)s\n"
            "• Documento registrado: %(vat_dup)s\n"
            "• Documento ingresado: %(vat_new)s"
        ) % {
            'name': duplicate.display_name,
            'vat_dup': duplicate.vat,
            'vat_new': vat,
        })

    # ============================================
    # CREATE
    # ============================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vat = vals.get('vat')
            if vat:
                duplicate = self._find_duplicate_vat(vat)
                if duplicate:
                    raise self._build_duplicate_error(duplicate, vat)

        return super().create(vals_list)

    # ============================================
    # WRITE
    # ============================================

    def write(self, vals):
        if 'vat' in vals:
            self._check_write_permission()

            vat = vals.get('vat')
            if vat:
                for partner in self:
                    duplicate = self._find_duplicate_vat(vat, exclude_ids=[partner.id])
                    if duplicate:
                        raise self._build_duplicate_error(duplicate, vat)

        return super().write(vals)

    # ============================================
    # PERMISOS
    # ============================================

    def _check_write_permission(self):
        """Verifica que el usuario tenga permiso para editar contactos"""
        if not self.env.user.has_group('mega_fix_module_contact.group_module_contact'):
            raise UserError(_(
                "No tienes permisos para editar contactos.\n"
                "Contacta al administrador.\n"
                "Grupo requerido: Module contact permissions"
            ))
