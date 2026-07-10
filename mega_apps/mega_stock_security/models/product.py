import logging
from odoo import models, api  # type: ignore
from odoo.exceptions import AccessError  # type: ignore

_logger = logging.getLogger(__name__)

GROUP = "mega_stock_security.group_inventory_adjustments"
GROUP_SALES = "mega_stock_security.group_inventory_adjustments_sales"


class ProductProduct(models.Model):
    _inherit = "product.product"

    def action_update_quantity_on_hand(self):
        # _logger.info("\n\n action_update_quantity_on_hand \n\n")
        if not self.env.user.has_group(GROUP):
            raise AccessError("No tiene permisos para actualizar cantidades de inventario, consulta con el administrador.")
        return super().action_update_quantity_on_hand()


class StockQuant(models.Model):
    _inherit = "stock.quant"

    # Por qué existe el bypass de self.env.su (auditoría 2026-07-10):
    # has_group() no tiene excepción para superusuario ni para sudo() (ver
    # odoo/addons/base/models/res_users.py, _has_group): comprueba membresía
    # real en el grupo, así que ni siquiera el cron "Procurement: run
    # scheduler" (corre como base.user_root) podía pasar el chequeo de
    # GROUP_SALES. En los flujos estándar de stock, el core reserva/libera
    # existencias internamente con self = self.sudo() antes de crear/escribir
    # stock.quant (stock/models/stock_quant.py: _update_available_quantity),
    # así que toda reserva, entrega, recepción, transferencia interna y el
    # scheduler quedaban bloqueados con el AccessError de este módulo.
    # self.env.su es True siempre que la ejecución actual está elevada por
    # sudo() -- sea quien sea quien la haya llamado, core u otro módulo --;
    # un usuario editando a mano stock.quant desde la UI nunca lo tiene en
    # True. Por eso sirve para separar "ejecución con sudo()" de "edición
    # manual" sin usar sudo() aquí ni debilitar la validación de grupo para
    # el caso manual, pero NO distingue si ese sudo() lo originó el core en
    # un flujo estándar de stock o un módulo de terceros.
    # Riesgo a revisar en el futuro: si se instala sh_pos_all_in_one_retail
    # (hoy 'uninstalled' en la BD, verificado 2026-07-10) o cualquier otro
    # módulo que llame sudo() directamente sobre stock.quant.write()/create()
    # fuera de los flujos estándar del core (caso encontrado:
    # sh_pos_cancel._sh_unreseve_qty, que hace
    # self.env['stock.quant'].sudo().search(...).write({'quantity': ...})),
    # ese código también heredará self.env.su=True y quedará autorizado sin
    # pertenecer a GROUP_SALES. Antes de instalar ese módulo (o cualquier
    # otro con sudo() sobre stock.quant), revisar esta validación.
    CAMPOS_SENSIBLES = {"inventory_quantity", "quantity", "reserved_quantity", "inventory_diff_quantity"}

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su and not self.env.user.has_group(GROUP_SALES):
            campos = set()
            for vals in vals_list:
                campos.update(self.CAMPOS_SENSIBLES.intersection(vals.keys()))
            _logger.warning(
                "Bloqueada creación manual no autorizada de stock.quant. "
                "Usuario: %s (id=%s). Campos: %s.",
                self.env.user.login, self.env.user.id, sorted(campos) or "N/A",
            )
            raise AccessError("No tiene permisos para crear/ajustar existencias (stock.quant).")
        return super().create(vals_list)

    def write(self, vals):
        campos_sensibles = self.CAMPOS_SENSIBLES.intersection(vals.keys())
        if campos_sensibles and not self.env.su and not self.env.user.has_group(GROUP_SALES):
            _logger.warning(
                "Bloqueada modificación manual no autorizada de stock.quant. "
                "Usuario: %s (id=%s). Campos: %s. IDs: %s.",
                self.env.user.login, self.env.user.id, sorted(campos_sensibles), self.ids,
            )
            raise AccessError("No tiene permisos para modificar cantidades de inventario.")
        return super().write(vals)
