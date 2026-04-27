import logging

from odoo import models, api  #type: ignore

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _mega_get_or_create_na_record(self, model_name):
        record = self.env[model_name].sudo().search([
            ("name", "=", "N/A")
        ], limit=1)

        if not record:
            record = self.env[model_name].sudo().create({
                "name": "N/A",
            })

        return record

    @api.model
    def cron_set_default_advisor_on_sale_orders(self):
        odoo_bot = self.env.ref(
            "base.user_root",
            raise_if_not_found=False
        )

        if not odoo_bot:
            _logger.warning("No se encontró el usuario OdooBot: base.user_root")
            return False

        orders = self.search([
            ("state", "=", "sale"),                 # Solo órdenes confirmadas
            ("invoice_status", "=", "to invoice"),  # Pendientes por facturar
            ("advisor_id", "=", False),
            ("vehicle", "=", False),
        ])

        for order in orders:
            vals = {}

            if "advisor_id" in order._fields and not order.advisor_id:
                vals["advisor_id"] = odoo_bot.id

            if "vehicle" in order._fields and not order.vehicle:
                vehicle_field = order._fields["vehicle"]

                if vehicle_field.type == "many2one":
                    na_vehicle = self._mega_get_or_create_na_record(
                        vehicle_field.comodel_name
                    )
                    vals["vehicle"] = na_vehicle.id

                elif vehicle_field.type in ("char", "text"):
                    vals["vehicle"] = "N/A"

            if vals:
                order.sudo().write(vals)

        return True
