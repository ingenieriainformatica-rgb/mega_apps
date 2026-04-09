from odoo import models, _  #type: ignore
from odoo.exceptions import AccessError  #type: ignore


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_cancel(self):
        """Solo permitir cancelar si el usuario pertenece al grupo autorizado."""
        # Si quieres permitir que el Admin (Settings) siempre pueda, déjalo así tal cual.
        # (El admin suele tener permisos amplios, pero esto refuerza por grupo.)
        if not self.env.user.has_group("mega_sale_cancel_group.group_sale_can_cancel_orders"):
            raise AccessError(_(
                "No tienes permisos para cancelar cotizaciones/órdenes.\n"
                "Solicita acceso al grupo: 'Administrador'."
            ))
        return super().action_cancel()