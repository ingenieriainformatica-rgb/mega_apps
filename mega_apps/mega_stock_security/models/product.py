import logging
from odoo import models  # type: ignore
from odoo.exceptions import AccessError  # type: ignore

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    def action_update_quantity_on_hand(self):
        # _logger.info("\n\n action_update_quantity_on_hand \n\n")
        if not self.env.user.has_group("mega_stock_security.group_inventory_adjustments"):
            raise AccessError("No tiene permisos para actualizar cantidades de inventario, consulta con el administrador.")
        return super().action_update_quantity_on_hand()
