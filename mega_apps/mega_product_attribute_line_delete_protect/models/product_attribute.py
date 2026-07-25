# -*- coding: utf-8 -*-

from odoo import models, _  # type: ignore
from odoo.exceptions import UserError  # type: ignore

_GROUP = "mega_product_attribute_line_delete_protect.group_product_attribute_line_manager"


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    def _check_attribute_manager(self):
        # `env.su` is True only for genuine superuser contexts such as module
        # installation/upgrade XML data loading (uid == SUPERUSER_ID). This
        # module never calls sudo() itself; this only recognizes privilege
        # Odoo's own framework already granted for that specific context.
        if self.env.su or self.env.user.has_group(_GROUP):
            return
        raise UserError(_(
            "Solo los usuarios autorizados para administrar atributos y "
            "variantes pueden realizar esta operación."
        ))

    def create(self, vals_list):
        if vals_list:
            self._check_attribute_manager()
        return super().create(vals_list)

    def write(self, values):
        if values:
            self._check_attribute_manager()
        return super().write(values)

    def unlink(self):
        self._check_attribute_manager()
        return super().unlink()
