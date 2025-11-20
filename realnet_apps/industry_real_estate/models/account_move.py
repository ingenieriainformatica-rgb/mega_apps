# Copyright (c) 2025-Present Realnet. (<https://realnet.com.co>)

from odoo import models, api, _
from odoo.exceptions import UserError


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    def _reverse_moves(self, default_values_list=None, cancel=False):
        """
        Sobreescribir _reverse_moves para preservar partner_id_manual_override en notas crédito.

        PROBLEMA IDENTIFICADO:
        Aunque partner_id_manual_override tiene copy=True, el partner_id se recalcula después
        del copy() debido a:
        1. _compute_partner_id() que se ejecuta en algún momento
        2. El write() que Odoo hace para invertir balances (línea 4891-4898)

        SOLUCIÓN:
        Guardar los partners manuales ANTES del copy y restaurarlos DESPUÉS del write de balances.
        """
        # PASO 1: Guardar líneas con override manual ANTES de crear la nota crédito
        lines_with_override = {}
        for move in self:
            for line in move.line_ids.filtered(lambda l: l.partner_id_manual_override):
                # Usar ID de línea como clave temporal
                lines_with_override[line.id] = {
                    'partner_id': line.partner_id.id,
                    'account_id': line.account_id.id,
                    'name': line.name or '',
                    'balance': line.balance,
                }

        # PASO 2: Ejecutar el _reverse_moves original
        reverse_moves = super(AccountMoveInherit, self)._reverse_moves(
            default_values_list=default_values_list,
            cancel=cancel
        )

        # PASO 3: Restaurar los partners manuales en las líneas de la nota crédito
        if lines_with_override:
            # Mapear líneas originales con líneas de nota crédito
            for move, reverse_move in zip(self, reverse_moves):
                for original_line in move.line_ids:
                    if original_line.id in lines_with_override:
                        override_data = lines_with_override[original_line.id]

                        # Buscar la línea correspondiente en la nota crédito
                        # (mismo account_id, name, balance invertido)
                        matching_line = reverse_move.line_ids.filtered(
                            lambda l: l.account_id.id == override_data['account_id']
                            and (l.name or '') == override_data['name']
                            and abs(l.balance + override_data['balance']) < 0.01  # balance invertido con tolerancia
                        )

                        if matching_line:
                            # Restaurar partner_id y el flag
                            matching_line.with_context(
                                skip_partner_override_update=True,
                                check_move_validity=False
                            ).write({
                                'partner_id': override_data['partner_id'],
                                'partner_id_manual_override': True
                            })

        return reverse_moves

    def _is_mandate_invoice(self):
        """
        Verificar si la factura es de tipo mandato.

        Returns:
            bool: True si es factura de mandato con operation_type == '11' (Mandatos)
        """
        self.ensure_one()
        # El campo l10n_co_edi_operation_type es un selection, no un Many2one
        # Por lo tanto, comparamos directamente con el string '11' que representa Mandatos
        is_mandate = (
            self.l10n_co_edi_operation_type == '11'
            and self.l10n_co_dian_mandate_principal
        )
        return is_mandate

    def _process_mandate_invoices(self):
        """
        Procesar facturas de mandato (l10n_co_edi_payment_option_id == 11).

        Para facturas de mandato:
        1. Obtener el mandante (l10n_co_dian_mandate_principal)
        2. Identificar las líneas contables que vienen de productos/servicios
        3. Cambiar el partner de esas líneas al mandante

        Lógica de identificación de cuenta:
        - La cuenta viene de product.property_account_income_id
        - Si no está definida, viene de product.categ_id.property_account_income_categ_id

        NOTA: Este método se ejecuta cada vez que se guarda la factura (borrador o confirmada)
        porque el método _sync_invoice() de Odoo core fuerza que todas las líneas tengan
        el mismo partner que la factura.
        """
        for move in self:

            # Verificar si es factura de mandato
            if not move._is_mandate_invoice():
                continue


            # Obtener el mandante
            mandate_principal = move.l10n_co_dian_mandate_principal

            # Procesar cada línea de factura (invoice_line_ids)
            for invoice_line in move.invoice_line_ids.filtered(lambda l: l.product_id):
                product = invoice_line.product_id

                # 1. Obtener la cuenta contable del producto
                #    Prioridad: product.property_account_income_id > category.property_account_income_categ_id
                income_account = product.property_account_income_id or \
                                product.categ_id.property_account_income_categ_id

                if not income_account:
                    continue  # Si no hay cuenta, saltar esta línea

                # 2. Buscar la(s) línea(s) contable(s) que usan esta cuenta
                journal_lines = move.line_ids.filtered(
                    lambda l: l.account_id == income_account
                    and l.display_type not in ('line_section', 'line_note')
                )

                # 3. Cambiar el partner al mandante en esas líneas
                if journal_lines:
                    journal_lines.with_context(
                        skip_partner_override_update=True,
                        check_move_validity=False
                    ).write({
                        'partner_id': mandate_principal.id,
                        'partner_id_manual_override': True  # Marcar como manual para que se conserve
                    })

    def _post(self, soft=True):
        """
        Sobreescribir el método _post para:
        1. Manejar facturas de mandato (payment_option_id == 11)
        2. Respetar el flag partner_id_manual_override en las líneas contables

        El código original de Odoo (líneas 5048-5053 de account_move.py) fuerza que
        todas las líneas tengan el mismo partner que la factura al confirmar.
        """

        # FUNCIONALIDAD 1: Procesar facturas de mandato ANTES del post original
        # Esto debe ejecutarse ANTES porque modifica los partners y marca el flag
        self._process_mandate_invoices()

        # FUNCIONALIDAD 2: Guardar líneas con override manual ANTES del post
        to_post = self if not soft else (self - self.filtered(lambda move: move.date > self.env.context_today()))

        lines_with_override = {}
        for invoice in to_post:
            if invoice.is_invoice():
                # Buscar líneas con override manual (incluye las de mandato que acabamos de marcar)
                manual_lines = invoice.line_ids.filtered(
                    lambda aml: aml.partner_id_manual_override
                    and aml.display_type not in ('line_note', 'line_section')
                )
                if manual_lines:
                    # Guardar el partner_id actual de cada línea con override
                    lines_with_override[invoice.id] = {
                        line.id: line.partner_id.id for line in manual_lines
                    }

        # Ejecutar el _post original (puede sobrescribir partners)
        result = super(AccountMoveInherit, self)._post(soft=soft)

        # FUNCIONALIDAD 3: Restaurar los partners manuales después del post
        for invoice in to_post:
            if invoice.id in lines_with_override:
                for line_id, partner_id in lines_with_override[invoice.id].items():
                    line = self.env['account.move.line'].browse(line_id)
                    if line.exists():
                        if line.partner_id.id != partner_id:
                            # Restaurar el partner original con contexto especial
                            line.with_context(
                                skip_partner_override_update=True,
                                check_move_validity=False
                            ).write({'partner_id': partner_id})
                            
        return result

    # @api.depends('line_ids')
    # def _compute_operation_type(self):
    #     """
    #     Sobrescribir _compute_operation_type() del módulo l10n_co_edi_mandate.

    #     PROBLEMA:
    #     El módulo l10n_co_edi_mandate cambia operation_type a '11' (Mandatos) para
    #     AMBOS tipos de facturas (out_invoice e in_invoice) cuando tienen productos
    #     con l10n_co_dian_mandate_contract=True.

    #     SOLUCIÓN:
    #     Solo aplicar la lógica de mandatos a facturas de cliente (out_invoice).
    #     Las facturas de proveedor (in_invoice) siempre deben quedar con operation_type='10'.
    #     """
    #     # Ejecutar el compute del padre (incluye l10n_co_edi_mandate)
    #     super()._compute_operation_type()

    #     # Corregir: Forzar operation_type='10' para facturas de proveedor
    #     for move in self:
    #         if move.move_type == 'in_invoice' and move.l10n_co_edi_operation_type == '11':
    #             move.l10n_co_edi_operation_type = '10'

    def write(self, vals):
        """
        Override de write para:
        1. Ejecutar la lógica original de Odoo (incluye _sync_dynamic_lines)
        2. Procesar facturas de mandato automáticamente al guardar borrador

        Este método se ejecuta cada vez que se guarda la factura (borrador o confirmada).
        El método _sync_invoice() de Odoo core (línea 3107) fuerza que todas las líneas
        tengan el mismo partner que la factura. Nosotros ejecutamos DESPUÉS para cambiar
        las líneas de productos al mandante.
        """

        # Ejecutar el write original (incluye toda la sincronización de Odoo)
        result = super().write(vals)

        # DESPUÉS del write, procesar facturas de mandato en borrador
        # Solo para facturas (no asientos manuales)
        for move in self.filtered(lambda m: m.is_invoice()):
            # Procesar si es mandato y está en borrador
            if move.state == 'draft' and move._is_mandate_invoice():
                move._process_mandate_invoices()

        return result
    
    def action_reset_to_draft_multi(self):
        invoices = self.filtered(lambda m: m.is_invoice(include_receipts=True))
        if not invoices:
            return True
        paid_states = {'paid','in_payment','partial'}
        blocked = invoices.filtered(lambda m: m.payment_state in paid_states)
        if blocked:
            names = ", ".join(blocked.mapped('name'))
            raise UserError(_("No se puede restablecer a borrador: hay facturas con pagos conciliados.\nRegistros: %s") % names)

        to_cancel = invoices.filtered(lambda m: m.state == 'posted')
        if to_cancel:
            to_cancel.sudo().button_cancel()

        to_draft = invoices.filtered(lambda m: m.state == 'cancel')
        if to_draft:
            to_draft.sudo().button_draft()

        for inv in invoices:
            inv.message_post(body=_("Restablecida a Borrador con sudo (acción masiva)."))
        return True
