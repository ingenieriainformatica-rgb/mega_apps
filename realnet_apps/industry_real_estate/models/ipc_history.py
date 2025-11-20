# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class IPCHistory(models.Model):
    _name = 'ipc.history'
    _description = 'Índice de Precios al Consumidor - Colombia'
    _order = 'year desc'

    name = fields.Char(compute='_compute_name', store=True)
    year = fields.Integer('Año', required=True)

    ipc_value = fields.Float('IPC %', digits=(16, 2), required=True,
                             help="Porcentaje de variación anual del IPC (ej: 13.25 para 13.25%)")

    # Metadatos
    source = fields.Char('Fuente', default='DANE')
    notes = fields.Text('Observaciones')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('applied', 'Aplicado')
    ], default='draft', string='Estado', required=True)

    active = fields.Boolean(default=True)

    # Compatible con Odoo 18 y 19
    try:
        # Odoo 19: Nueva sintaxis con models.Constraint
        _unique_period = models.Constraint(
            'UNIQUE(year)',
            'Ya existe un registro de IPC para este período!'
        )
    except AttributeError:
        # Odoo 18: Sintaxis antigua con _sql_constraints
        _sql_constraints = [
            ('unique_period', 'UNIQUE(year)',
             'Ya existe un registro de IPC para este período!')
        ]

    @api.depends('year')
    def _compute_name(self):
        for record in self:
            if not record.exists():
                continue
            if record.year:
                record.name = f"IPC {record.year}"

    # ========== MÉTODOS DE CAMBIO DE ESTADO ==========

    # def action_confirmed(self):
    #     """Confirmar el registro de IPC"""
    #     # for record in self:
    #     #     if record.state != 'draft':
    #     #         raise UserError(_('Solo se pueden confirmar registros en estado Borrador.'))
    #     #     record.write({'state': 'confirmed'})
    #     # return True
    #     raise UserError(_("Esta acción está deshabilitada temporalmente."))
        

    def action_set_to_draft(self):
        """Volver a Borrador"""
        for record in self:
            if record.state == 'applied':
                raise UserError(_('No se puede volver a Borrador un IPC que ya ha sido aplicado a contratos.'))
            record.write({'state': 'draft'})
        return True

    def action_mark_as_applied(self):
        """Marcar como Aplicado (usado cuando se aplica a contratos)"""
        for record in self:
            if record.state != 'confirmed':
                raise UserError(_('Solo se pueden marcar como aplicados los registros confirmados.'))
            record.write({'state': 'applied'})
        return True

    # ========== RESTRICCIONES DE ESCRITURA Y ELIMINACIÓN ==========

    def write(self, vals):
        """Restricciones de edición según el estado"""
        for record in self:
            # No permitir edición de campos críticos si está confirmado o aplicado
            if record.state in ('confirmed', 'applied'):
                protected_fields = {'year', 'ipc_value'}
                if any(field in vals for field in protected_fields):
                    raise UserError(_(
                        'No se pueden modificar los valores de un IPC que ya está confirmado o aplicado. '
                        'Debe volver a estado Borrador primero.'
                    ))

            # Si está aplicado, solo usuarios con acceso a Ajustes pueden modificar estado
            if record.state == 'applied' and 'state' in vals:
                if not self.env.user.has_group('base.group_erp_manager'):
                    raise UserError(_('Solo los usuarios con acceso a Ajustes pueden modificar registros de IPC aplicados.'))

        return super(IPCHistory, self).write(vals)

    def unlink(self):
        """Restricciones de eliminación según estado y permisos del usuario"""
        for record in self:
            # NUNCA se puede eliminar un registro aplicado
            if record.state == 'applied':
                raise UserError(_(
                    'No se puede eliminar el IPC "%s" porque ya ha sido aplicado a contratos. '
                    'Puede archivarlo en su lugar.'
                ) % record.name)

            # Registros confirmados solo pueden ser eliminados por usuarios con acceso a Ajustes
            if record.state == 'confirmed':
                if not self.env.user.has_group('base.group_erp_manager'):
                    raise UserError(_(
                        'No tiene permisos para eliminar el IPC "%s" que está confirmado. '
                        'Solo los usuarios con acceso a Ajustes pueden eliminar registros confirmados.'
                    ) % record.name)

            # Registros en borrador pueden ser eliminados por cualquier usuario con permisos de escritura

        return super(IPCHistory, self).unlink()

    # ========== VALIDACIONES ==========

    @api.constrains('year')
    def _check_year(self):
        """Validar que el año sea razonable"""
        for record in self:
            if record.year and (record.year < 1900 or record.year > 2200):
                raise ValidationError(_('El año debe estar entre 1900 y 2200.'))
