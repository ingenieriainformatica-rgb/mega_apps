import logging
from odoo import api, fields, models, _  #type: ignore
from odoo.exceptions import ValidationError  #type: ignore

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.constrains('warehouse_id')
    def _check_warehouse_required(self):
        for order in self:
            if not order.warehouse_id:
                raise ValidationError(
                    _("Debe seleccionar un almacén para la orden de venta %s.")
                    % (order.name or '')
                )

    @api.model
    def default_get(self, fields_list):
        """Extiende los defaults de sale.order sin romper la estructura."""
        # SIEMPRE arrancamos del super y guardamos el resultado
        res = super().default_get(fields_list)

        # Solo por seguridad, si por alguna razón res viene None, lo forzamos a dict
        if res is None:
            _logger.warning("default_get devolvió None en sale.order, inicializando dict vacío.")
            res = {}

        # ---- Aquí metes tu lógica de almacén si quieres ----
        if 'warehouse_id' in fields_list:
            company = self.env.company
            warehouses = self.env['stock.warehouse'].search([
                ('company_id', '=', company.id),
            ])
            # Si hay más de un almacén, no ponemos ninguno por defecto
            if len(warehouses) > 1:
                res['warehouse_id'] = False

        return res
    
    
    @api.onchange('company_id')
    def _onchange_company_id(self):
        """Evitar que Odoo vuelva a poner un almacén por defecto
        cuando se seleccione la compañía (por ejemplo al escoger el cliente).
        """
        # Llamamos primero a la lógica estándar
        res = super()._onchange_company_id()

        company = self.company_id or self.env.company
        warehouses = self.env['stock.warehouse'].search([
            ('company_id', '=', company.id),
        ])

        # Si la compañía tiene MÁS de un almacén, no queremos default automático
        if len(warehouses) > 1:
            # Solo si no viene un default forzado en el contexto (por otros flujos)
            if not self.env.context.get('default_warehouse_id'):
                self.warehouse_id = False

        return res
    

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        res = super()._onchange_partner_id()

        company = self.company_id or self.env.company
        warehouses = self.env['stock.warehouse'].search([
            ('company_id', '=', company.id),
        ])

        if len(warehouses) > 1 and not self.env.context.get('default_warehouse_id'):
            self.warehouse_id = False

        return res
    
    @api.onchange('user_id')
    def _onchange_user_id_reset_warehouse(self):
        """Cada vez que cambie el vendedor, vaciamos warehouse_id."""
        for order in self:
            if order.state in ('draft', 'sent', 'cancel'):
                order.warehouse_id = False
