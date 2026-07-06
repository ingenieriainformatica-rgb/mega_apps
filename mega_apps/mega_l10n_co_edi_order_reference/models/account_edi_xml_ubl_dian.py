# -*- coding: utf-8 -*-
"""Personaliza cac:OrderReference en el XML UBL-DIAN.

Diagnóstico (ver detalle completo entregado al usuario):
- l10n_co_dian en esta instalación NO usa el sistema nuevo de document_node /
  _add_invoice_header_nodes: el parámetro de sistema
  'account_edi_ubl_cii.use_new_dict_to_xml_helpers' no está activo, así que
  `_export_invoice` sigue el camino viejo (plantillas QWeb + `vals['vals']`).
- El nodo cac:OrderReference se renderiza siempre por
  `ubl_20_templates.xml` (plantilla ubl_20_CommonType) con
  `vals.get('order_reference')` como cbc:ID. `l10n_co_dian._export_invoice_vals`
  (account_edi_xml_ubl_dian.py:553) calcula ese valor heredándolo de
  account_edi_ubl_cii (`invoice.ref or invoice.name`) y ya fuerza
  `sales_order_id=False` y no define `order_issue_date`.
- `cleanup_xml_node` (odoo/tools/xml_utils.py) elimina en cascada cualquier
  nodo hoja totalmente vacío. Como sales_order_id/order_issue_date ya están
  siempre vacíos para DIAN, basta con controlar `order_reference`: si lo
  dejamos en False, cac:OrderReference completo desaparece del XML solo.
- No usamos `_inherit = 'account.edi.xml.ubl_dian'` porque ese modelo hereda
  transitivamente de una copia de `account_edi_ubl_cii` empaquetada en la
  imagen Docker (/usr/lib/python3/dist-packages) cuyo `_inherit` interno
  apunta a un modelo inexistente ('account.edi.ubl'): cualquier módulo que
  declare un nuevo fragmento _inherit sobre esa cadena hace que Odoo falle al
  recalcular ir.model.inherit. Como no se puede tocar addons_path ni esa
  copia empaquetada, parcheamos el método directamente sobre la clase Python
  ya cargada de l10n_co_dian.
"""
import logging

from odoo.addons.l10n_co_dian.models.account_edi_xml_ubl_dian import AccountEdiXmlUBLDian

_logger = logging.getLogger(__name__)

_TARGET_PARTNER_NAME = 'ALFRED SAS'
_TARGET_PARTNER_VAT_DIGITS = '9013414108'

_original_export_invoice_vals = AccountEdiXmlUBLDian._export_invoice_vals


def _mega_export_invoice_vals(self, invoice):
    vals = _original_export_invoice_vals(self, invoice)

    partner = invoice.partner_id
    order_ref = (invoice.customer_order_ref or '').strip()
    partner_name = (partner.name or '').strip()
    vat_digits = ''.join(ch for ch in (partner.vat or '') if ch.isdigit())
    is_target_client = partner_name == _TARGET_PARTNER_NAME and vat_digits == _TARGET_PARTNER_VAT_DIGITS
    apply_custom = is_target_client and bool(order_ref)

    _logger.info(
        "[mega_l10n_co_edi_order_reference] Factura=%s | Cliente=%s | VAT=%s | "
        "N° orden=%r | Aplica personalización=%s",
        invoice.name, partner.name, partner.vat, order_ref, apply_custom,
    )

    # cac:OrderReference/cbc:ID es el único dato variable que queda en el nodo
    # para documentos DIAN (sales_order_id y order_issue_date ya van siempre
    # vacíos). Ponerlo en False hace que cleanup_xml_node elimine el nodo
    # completo por estar totalmente vacío.
    vals['vals']['order_reference'] = order_ref if apply_custom else False

    return vals


AccountEdiXmlUBLDian._export_invoice_vals = _mega_export_invoice_vals
