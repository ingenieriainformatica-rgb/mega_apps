# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError

GROUP_XML_ID = 'mega_credit_note_copy_invoice_data.group_credit_note_vehicle_backfill'
BATCH_SIZE = 200


class CreditNoteVehicleBackfillWizard(models.TransientModel):
    _name = 'mega.credit.note.vehicle.backfill.wizard'
    _description = 'Actualización histórica de Vehículo en notas crédito'

    date_from = fields.Date(string='Fecha inicial')
    date_to = fields.Date(string='Fecha final')
    note_type = fields.Selection([
        ('customer', 'Notas crédito de clientes'),
        ('vendor', 'Notas crédito de proveedores'),
        ('both', 'Ambas'),
    ], string='Tipo', default='both', required=True)

    state = fields.Selection([
        ('draft', 'Configuración'),
        ('preview', 'Vista previa'),
        ('done', 'Actualizado'),
    ], default='draft', required=True)

    count_found = fields.Integer(string='Notas crédito encontradas', readonly=True)
    count_to_update = fields.Integer(string='Notas crédito por actualizar', readonly=True)
    count_skipped = fields.Integer(string='Notas crédito omitidas', readonly=True)

    @api.onchange('date_from', 'date_to', 'note_type')
    def _onchange_filters(self):
        self.update({
            'state': 'draft',
            'count_found': 0,
            'count_to_update': 0,
            'count_skipped': 0,
        })

    def _check_backfill_group(self):
        if not self.env.user.has_group(GROUP_XML_ID):
            raise AccessError(_(
                "No tiene permisos para actualizar el vehículo en notas crédito históricas.\n"
                "Solicite acceso al grupo: 'Actualizar vehículo en notas crédito históricas'."
            ))

    def _get_domain(self):
        self.ensure_one()
        if self.note_type == 'customer':
            domain = [('move_type', '=', 'out_refund')]
        elif self.note_type == 'vendor':
            domain = [('move_type', '=', 'in_refund')]
        else:
            domain = [('move_type', 'in', ('out_refund', 'in_refund'))]
        domain.append(('reversed_entry_id', '!=', False))
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        return domain

    def _split_candidates(self):
        """Devuelve (notas_encontradas, notas_por_actualizar) según las reglas de
        omisión: sin factura origen (ya excluido por el dominio), factura origen
        sin vehículo, o nota crédito que ya tiene vehículo."""
        self.ensure_one()
        found = self.env['account.move'].search(self._get_domain())
        to_update = found.filtered(
            lambda move: not move.vehicle and move.reversed_entry_id.vehicle
        )
        return found, to_update

    def _reopen_view(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_preview(self):
        self.ensure_one()
        self._check_backfill_group()
        found, to_update = self._split_candidates()
        self.write({
            'count_found': len(found),
            'count_to_update': len(to_update),
            'count_skipped': len(found) - len(to_update),
            'state': 'preview',
        })
        return self._reopen_view()

    def action_update(self):
        self.ensure_one()
        self._check_backfill_group()
        found, to_update = self._split_candidates()

        to_update_ids = to_update.ids
        for offset in range(0, len(to_update_ids), BATCH_SIZE):
            batch_ids = to_update_ids[offset:offset + BATCH_SIZE]
            for move in self.env['account.move'].browse(batch_ids):
                origin = move.reversed_entry_id
                move.write({'vehicle': origin.vehicle})
                move.message_post(
                    body=_('Vehículo recuperado desde la factura origen %s.') % (origin.display_name or origin.name or origin.id)
                )

        self.write({
            'count_found': len(found),
            'count_to_update': len(to_update),
            'count_skipped': len(found) - len(to_update),
            'state': 'done',
        })
        return self._reopen_view()
