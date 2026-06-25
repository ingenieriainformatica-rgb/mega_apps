# -*- coding: utf-8 -*-

from odoo import models, _  # type: ignore
from odoo.exceptions import UserError  # type: ignore

_GROUP = "mega_product_attribute_line_delete_protect.group_product_attribute_line_manager"


class ProductTemplateAttributeLine(models.Model):
    _inherit = "product.template.attribute.line"

    def unlink(self):
        if self.env.user.has_group(_GROUP):
            return super().unlink()
        raise UserError(_(
            "No tienes permisos para eliminar líneas de atributos.\n\n"
            "Esta acción está restringida para proteger las variantes del producto. "
            "Solicita autorización a un usuario con el grupo "
            "\"Administrador de atributos de producto\"."
        ))

    def action_unlink_protected(self):
        self.unlink()
        return False
