# -*- coding: utf-8 -*-

from odoo import models, _  # type: ignore
from odoo.exceptions import UserError  # type: ignore

_GROUP = "mega_product_attribute_line_delete_protect.group_product_attribute_line_manager"


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    def _check_attribute_manager(self):
        # See product_attribute.py: env.su only reflects genuine superuser
        # contexts (e.g. module install/upgrade data loading), never a
        # regular user's own sudo() call from this module.
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
