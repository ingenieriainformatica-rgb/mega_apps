# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError

# XML IDs de variantes bloqueadas (los que pusiste en tu XML)
_LOCKED_VARIANT_XMLIDS = [
    'industry_real_estate.product_product_42',
    'industry_real_estate.product_product_43',
    'industry_real_estate.product_product_44',
    'industry_real_estate.product_product_45',
    'industry_real_estate.product_product_46',
    'industry_real_estate.product_product_47',
    'industry_real_estate.product_product_48',
    'industry_real_estate.product_product_49',
    'industry_real_estate.product_product_50'
]

def _collect_locked_variant_ids(env):
    """Convierte xmlids -> ids (ignora los que no existan)."""
    ids = []
    for xid in _LOCKED_VARIANT_XMLIDS:
        rec = env.ref(xid, raise_if_not_found=False)
        if rec:
            ids.append(rec.id)
    return set(ids)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _is_admin_user(self):
        """
        Verifica si el usuario actual es administrador.
        Retorna True si el usuario tiene permisos de administrador.
        """
        return self.env.user.has_group('base.group_system')

    def _assert_not_locked(self):
        """
        Valida que productos protegidos solo puedan ser editados por administradores.
        - Administradores: pueden editar/eliminar
        - Usuarios normales: NO pueden editar/eliminar
        """
        if not self:
            return

        # Si es administrador, permitir la operación
        if self._is_admin_user():
            return

        # Si NO es administrador, verificar si intenta modificar productos protegidos
        locked = _collect_locked_variant_ids(self.env)
        if any(pid in locked for pid in self.ids):
            raise UserError(_("Este producto está protegido por el sistema y solo puede ser modificado por administradores."))

    def write(self, vals):
        self._assert_not_locked()
        return super().write(vals)

    def unlink(self):
        self._assert_not_locked()
        return super().unlink()


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _is_admin_user(self):
        """
        Verifica si el usuario actual es administrador.
        Retorna True si el usuario tiene permisos de administrador.
        """
        return self.env.user.has_group('base.group_system')

    def _assert_not_locked(self):
        """
        Valida que productos protegidos solo puedan ser editados por administradores.
        - Administradores: pueden editar/eliminar
        - Usuarios normales: NO pueden editar/eliminar
        """
        if not self:
            return

        # Si es administrador, permitir la operación
        if self._is_admin_user():
            return

        # Si NO es administrador, verificar si intenta modificar productos con variantes protegidas
        locked = _collect_locked_variant_ids(self.env)
        if self.mapped('product_variant_ids').filtered(lambda v: v.id in locked):
            raise UserError(_("Este producto está protegido por el sistema y solo puede ser modificado por administradores."))

    def write(self, vals):
        self._assert_not_locked()
        return super().write(vals)

    def unlink(self):
        self._assert_not_locked()
        return super().unlink()
