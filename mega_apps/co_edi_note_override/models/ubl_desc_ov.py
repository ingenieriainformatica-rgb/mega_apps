import logging
from odoo import models

_logger = logging.getLogger(__name__)


class AccountEdiXmlUBL20(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_20'

    def _prepend_custom_description_note(self, data, move):
        """Inserta x_studio_descripcin_1 como primera nota (cbc:Note) si existe.
           Soporta invoice, credit_note y debit_note.
        """
        try:
            inv_vals = data.get('vals') or {}
            raw_desc = getattr(move, 'x_studio_descripcin_1', '') or ''
            # Normaliza y recorta por prudencia DIAN (cbc:Note máx. 12 chars aprox.)
            desc = ' '.join(raw_desc.split()).strip()[:12]
            if not desc:
                return data

            notes = inv_vals.get('note_vals') or []
            if not isinstance(notes, list):
                notes = []
            # Forzamos estructura [{'note': '...'}]
            notes = [
                n if isinstance(n, dict) and 'note' in n else {'note': str(n)}
                for n in notes
            ]

            # Evita duplicado si ya es la primera
            if not (notes and notes[0].get('note', '') == desc):
                inv_vals['note_vals'] = [{'note': desc}] + notes
                _logger.info("DIAN: se agregó descripción como primera nota a %s (%s).",
                             move.display_name, data.get('document_type'))
            else:
                _logger.debug("DIAN: descripción ya estaba como primera nota en %s.", move.display_name)
        except Exception:
            _logger.exception("DIAN: error ajustando note_vals para %s", move.display_name)
        return data
    
    # Factura, note credit, note debit
    def _export_invoice_vals(self, invoice, **kwargs):
        data = super()._export_invoice_vals(invoice, **kwargs)
        return self._prepend_custom_description_note(data, invoice)
    