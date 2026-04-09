import logging
import re
from datetime import datetime

from odoo import api, fields, models, _  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore

_logger = logging.getLogger(__name__)

DIGITOS = 6

class AccountMove(models.Model):
    _inherit = 'account.move'

    _REF_MOVE_TYPES = ('in_invoice',)

    def _sanitize_ref_value(self, ref):
        """Quita todos los espacios en blanco del valor."""
        if not ref:
            return ref
        return re.sub(r'\s+', '', ref)

    def _get_ref_validation_cutoff(self):
        """
        Fecha de corte desde la cual aplica la validación.
        Ajusta este valor según necesidad.
        """
        return datetime(2026, 4, 9, 0, 0, 0)

    def _should_validate_ref_for_move(self, move):
        """
        Define si a este documento se le debe aplicar la validación.
        """
        if move.move_type not in self._REF_MOVE_TYPES:
            return False

        if not move.ref:
            return False

        if not move.create_date:
            return False

        move_create_date = fields.Datetime.to_datetime(move.create_date)
        return move_create_date >= self._get_ref_validation_cutoff()

    def _validate_ref_length_limit(self):
        for move in self:
            if not self._should_validate_ref_for_move(move):
                _logger.info(
                    "\n\nValidación omitida | move_id=%s | move_type=%s | create_date=%s | ref=%s\n\n",
                    move.id, move.move_type, move.create_date, move.ref
                )
                continue

            ref_clean = move._sanitize_ref_value(move.ref)

            if len(ref_clean) > DIGITOS:
                raise ValidationError(_(
                    "Debe digitar únicamente los últimos %d caracteres de la factura del proveedor.\n\n"
                    "Valor actual: %s\n"
                    "Longitud encontrada: %s"
                ) % (DIGITOS, ref_clean, len(ref_clean)))

    def _validate_ref_uniqueness(self):
        for move in self:
            if not self._should_validate_ref_for_move(move):
                continue

            if not move.partner_id:
                continue

            ref_clean = self._sanitize_ref_value(move.ref)

            domain = [
                ('ref', '=', ref_clean),
                ('partner_id', '=', move.partner_id.id),
                ('move_type', 'in', self._REF_MOVE_TYPES),
                ('id', '!=', move.id),
            ]

            existing = self.search(domain, limit=1)
            if existing:
                raise ValidationError(_(
                    "Ya existe un documento con la misma referencia '%s' y contacto '%s'.\n"
                    "Documento existente: %s (ID: %s)"
                ) % (ref_clean, move.partner_id.name, existing.name, existing.id))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            ref = vals.get('ref')
            if ref:
                vals['ref'] = self._sanitize_ref_value(ref)

        records = super().create(vals_list)
        records._validate_ref_length_limit()
        records._validate_ref_uniqueness()
        return records

    def write(self, vals):
        vals = dict(vals)

        validate_ref = 'ref' in vals
        validate_partner = 'partner_id' in vals

        if validate_ref and vals.get('ref'):
            vals['ref'] = self._sanitize_ref_value(vals['ref'])

        result = super().write(vals)

        # Solo validar cuando realmente cambien ref
        if validate_ref:
            self._validate_ref_length_limit()

        if validate_ref or validate_partner:
            self._validate_ref_uniqueness()

        return result
