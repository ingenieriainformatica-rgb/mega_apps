import logging
from odoo import api, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _check_all_delivered(self):
        """Lanza error si hay productos (product/consu) sin entregar."""
        for order in self:
            pickings = order.picking_ids.filtered(
                lambda p: p.picking_type_id.code == "outgoing" and p.state != "cancel"
            )
            pending = pickings.filtered(lambda p: p.state != "done")
            if pending:
                names = ", ".join(pending.mapped("name"))
                raise ValidationError(_(
                    "No puede crear la factura porque hay entregas pendientes: %s.\n"
                    "Valide los albaranes primero."
                ) % names)

    # Botón principal "Crear factura"
    def action_create_invoice(self):
        self._check_all_delivered()
        return super().action_create_invoice()

    # Respaldo: algunos flujos llaman directo a _create_invoices
    def _create_invoices(self, grouped=False, final=False):
        self._check_all_delivered()
        return super()._create_invoices(grouped=grouped, final=final)
