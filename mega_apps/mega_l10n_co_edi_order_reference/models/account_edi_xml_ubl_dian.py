# -*- coding: utf-8 -*-
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountEdiXmlUblDian(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_dian'

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)

        invoice = vals['invoice']
        partner = invoice.partner_id
        order_ref = (invoice.customer_order_ref or '').strip()
        send_order_reference = bool(partner.x_send_order_reference_dian) and bool(order_ref)

        _logger.info(
            "[mega_l10n_co_edi_order_reference] Factura=%s | Cliente=%s | "
            "x_send_order_reference_dian=%s | N° orden=%r | OrderReference generado=%s",
            invoice.name, partner.display_name,
            partner.x_send_order_reference_dian, order_ref, send_order_reference,
        )

        document_node['cac:OrderReference'] = {
            'cbc:ID': {'_text': order_ref},
        } if send_order_reference else None
