# Copyright (c) 2025-Present Realnet. (<https://realnet.com.co>)

from odoo import models, fields, api


class AccountMoveLineInherit(models.Model):
    _inherit = 'account.move.line'

    # Campo técnico para marcar cuando el partner se ha cambiado manualmente
    partner_id_manual_override = fields.Boolean(
        string='Partner Manual Override',
        default=False,
        copy=True,  # CAMBIADO: copy=True para que se copie en notas crédito y duplicados
        help='Campo técnico que indica si el partner_id fue establecido manualmente '
             'y no debe ser recalculado automáticamente desde el move_id.'
    )

    # =================================================================================
    # MÉTODO 1: _compute_partner_id (PROTECCIÓN ADICIONAL - Opcional pero recomendado)
    # =================================================================================
    # IMPORTANTE: No agregar @api.depends aquí
    # El código original de Odoo dice: "Do not depend on `move_id.partner_id`, the inverse is taking care of that"
    def _compute_partner_id(self):
        """
        Sobreescribir el método de cálculo del partner_id para respetar
        los cambios manuales realizados por el usuario.

        NOTA: Este método es una capa de protección adicional, pero NO es crítico
        porque el método _post() en account_move.py ya maneja la restauración.

        Se mantiene como protección en casos edge donde Odoo invalide el cache.
        """
        for line in self:
            if not line.exists():
                continue
            # Solo recalcular si NO hay override manual
            if not line.partner_id_manual_override:
                line.partner_id = line.move_id.partner_id.commercial_partner_id
            # Si hay override manual, conservar el valor actual (no hacer nada)

    # =================================================================================
    # MÉTODO 2: _inverse_partner_id (CRÍTICO - ABSOLUTAMENTE NECESARIO)
    # =================================================================================
    @api.onchange('partner_id')
    def _inverse_partner_id(self):
        """
        Método inverso que se ejecuta cuando el usuario cambia manualmente el partner_id.

        CRÍTICO: Este es el ÚNICO método que marca el flag cuando el usuario
        cambia el partner en la UI. Sin este método, toda la funcionalidad falla.

        Flujo:
        1. Usuario cambia partner en la UI
        2. @api.onchange se dispara
        3. Este método marca partner_id_manual_override = True
        4. El método _post() en account_move.py ve el flag y protege la línea
        """
        # Primero ejecutar la lógica original (recalcula account_id si es necesario)
        super(AccountMoveLineInherit, self)._inverse_partner_id()

        # Marcar el override cuando el partner difiere del move
        for line in self:
            if line.move_id and line.partner_id:
                expected_partner = line.move_id.partner_id.commercial_partner_id
                # Si el partner es diferente al esperado, marcar override
                if line.partner_id != expected_partner:
                    line.partner_id_manual_override = True
                else:
                    # Si vuelve a coincidir, quitar el flag
                    line.partner_id_manual_override = False

    # =================================================================================
    # MÉTODO 3: write() (IMPORTANTE - Simplificado)
    # =================================================================================
    def write(self, vals):
        """
        Interceptar write para manejar el flag de override cuando se modifica partner_id.

        IMPORTANTE: Este método persiste el flag a la BD y maneja casos de API/imports.

        SIMPLIFICADO: La lógica compleja anterior no era necesaria porque _post()
        ya hace backup/restore. Ahora solo marcamos el flag cuando corresponde.
        """
        # Si se está escribiendo partner_id directamente
        if 'partner_id' in vals and not self.env.context.get('skip_partner_override_update'):
            # Determinar si necesitamos actualizar el flag
            for line in self:
                if line.move_id:
                    expected_partner_id = line.move_id.partner_id.commercial_partner_id.id
                    new_partner_id = vals.get('partner_id')

                    # Lógica simple: ¿El nuevo partner es diferente al esperado?
                    if new_partner_id and new_partner_id != expected_partner_id:
                        # Marcar override en el mismo write
                        vals['partner_id_manual_override'] = True
                    elif new_partner_id == expected_partner_id:
                        # Si vuelve al original, quitar el flag
                        vals['partner_id_manual_override'] = False

            # Ejecutar el write original con el flag actualizado
            return super(AccountMoveLineInherit, self).write(vals)
        else:
            # Si no se está modificando partner_id, solo ejecutar el write normal
            return super(AccountMoveLineInherit, self).write(vals)
