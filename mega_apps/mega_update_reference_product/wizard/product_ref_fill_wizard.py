# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ProductRefFillWizard(models.TransientModel):
    _name = "product.ref.fill.wizard"
    _description = "Asignar default_code a archivados sin referencia"

    def action_clear_refs(self):
        """Vacía el default_code de todos los productos inactivos y marca el nombre (UP)."""
        Product = self.env["product.product"].with_context(active_test=False)

        # Buscar todos los productos inactivos
        # products = Product.search([("active", "=", False)])
        products = Product.search([
            ("active", "=", False),
            "|", ("default_code", "!=", False), ("default_code", "!=", ""),
        ])
        count = len(products)

        if not products:
            return {
                "effect": {
                    "fadeout": "slow",
                    "message": _("No hay productos inactivos para actualizar."),
                    "type": "rainbow_man",
                }
            }

        # Limpiar default_code y marcar nombre con (UP)
        for p in products:
            new_name = p.name or ""
            if "(UP)" not in new_name:  # evitar duplicar la marca
                new_name = f"{new_name.strip()} (UP)"
            p.write({
                "default_code": False,
                "name": new_name,
            })

        # Efecto visual
        return {
            "effect": {
                "fadeout": "slow",
                "message": _("✅ Se limpiaron %s productos inactivos y se marcaron como (UP).") % count,
                "type": "rainbow_man",
            }
        }
