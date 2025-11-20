# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _  # type: ignore
from odoo.tools import html_escape  # type: ignore
from markupsafe import Markup, escape  # type: ignore



_logger = logging.getLogger(__name__)

STATE_TO_INVOICE= 'to invoice'
INVOICED= 'invoiced'


class SaleOrder(models.Model):
    _inherit = "sale.order"

    show_to_invoice_with_posted = fields.Boolean(
        string="Mostrar botón 'Revisar facturación'",
        help="Verdadero si invoice_status es 'to invoice' y ya hay al menos una factura contabilizada.",
        default=False,
    )

    def action_open_posted_invoices(self):
        self.sudo().write({'invoice_status': INVOICED, 'show_to_invoice_with_posted': False})
        body = Markup(
            f"<p><b>{escape(_('Actualización de estado'))}</b></p>"
            f"<ul><li>Por facturar -> Facturado por completo</li></ul>"
        )
        self.message_post(
            body=body,  # 👈 HTML seguro
            message_type='comment',
            subtype_xmlid='mail.mt_note',  # nota interna
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
            "effect": {
                "fadeout": "slow",
                "message": _("Actualización exitosa. Orden %s actualizada.", self.name),
                "type": "rainbow_man",  # animación/overlay de éxito
            },
        }


    @api.model
    def _cron_flag_orders_to_invoice_with_posted(self):
      cr = self.env.cr
      sql = """
          SELECT
              so.id,
              so.name,
              so.invoice_status,
              COUNT(DISTINCT am.id) AS invoices_total
          FROM sale_order so
          LEFT JOIN sale_order_line             sol ON sol.order_id = so.id
          LEFT JOIN sale_order_line_invoice_rel r   ON r.order_line_id = sol.id
          LEFT JOIN account_move_line           aml ON aml.id = r.invoice_line_id
          LEFT JOIN account_move                am  ON am.id = aml.move_id
          WHERE so.invoice_status = %s
          GROUP BY so.id, so.name, so.invoice_status
          HAVING COUNT(DISTINCT am.id) > 0
          ORDER BY so.id
      """
      cr.execute(sql, (STATE_TO_INVOICE,))
      ids_true = [row[0] for row in cr.fetchall()]
      if ids_true:
          self.sudo().browse(ids_true).write({'show_to_invoice_with_posted': True})
          _logger.info("Marcadas %s OV con show_to_invoice_with_posted=True", len(ids_true))
      else:
          _logger.info("No se encontraron OV para marcar en True.")
