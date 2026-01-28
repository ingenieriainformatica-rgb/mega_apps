import logging
from odoo import models, api  # type: ignore
from odoo.exceptions import AccessError  # type: ignore

_logger = logging.getLogger(__name__)

GROUP = "mega_stock_security.group_inventory_adjustments"


class ProductProduct(models.Model):
    _inherit = "product.product"

    def action_update_quantity_on_hand(self):
        # _logger.info("\n\n action_update_quantity_on_hand \n\n")
        if not self.env.user.has_group(GROUP):
            raise AccessError("No tiene permisos para actualizar cantidades de inventario, consulta con el administrador.")
        return super().action_update_quantity_on_hand()


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group(GROUP):
            raise AccessError("No tiene permisos para crear/ajustar existencias (stock.quant).")
        return super().create(vals_list)

    def write(self, vals):
        # si quieres permitir ediciones “inofensivas”, filtra aquí.
        # Por ejemplo, bloquear solo campos sensibles:
        campos_sensibles = {"inventory_quantity", "quantity", "reserved_quantity", "inventory_diff_quantity"}
        if campos_sensibles.intersection(vals.keys()) and not self.env.user.has_group(GROUP):
            raise AccessError("No tiene permisos para modificar cantidades de inventario.")
        return super().write(vals)