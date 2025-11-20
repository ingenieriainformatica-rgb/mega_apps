# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ========== CAMPOS NUEVOS ==========

    support_doc_validation_override = fields.Boolean(
        string='Validación de Secuencia Anulada',
        default=False,
        help='Si está marcado, permite confirmar sin validar documento anterior. '
             'Solo usuarios autorizados pueden modificar este campo.',
        tracking=True,
    )

    previous_support_doc_id = fields.Many2one(
        'account.move',
        string='Documento Soporte Anterior',
        compute='_compute_previous_support_doc',
        store=False,
        help='Documento soporte inmediatamente anterior en la secuencia del mismo journal'
    )

    previous_support_doc_dian_state = fields.Selection(
        selection=[
            ('invoice_sending_failed', "Sending Failed"),
            ('invoice_pending', "Pending"),
            ('invoice_rejected', "Rejected"),
            ('invoice_accepted', "Accepted"),
        ],
        string='Estado DIAN del Anterior',
        compute='_compute_previous_support_doc',
        store=False,
        help='Estado de envío a DIAN del documento anterior'
    )

    show_support_doc_warning = fields.Boolean(
        string='Mostrar Advertencia de Secuencia',
        compute='_compute_show_support_doc_warning',
        help='Indica si debe mostrarse advertencia por documento anterior no enviado'
    )

    # ========== MÉTODOS COMPUTADOS ==========

    @api.depends('name', 'journal_id', 'l10n_co_edi_is_support_document', 'state')
    def _compute_previous_support_doc(self):
        """Calcula el documento soporte anterior en la secuencia y su estado DIAN"""
        for move in self:
            _logger.info(
                "🔍 [COMPUTE] Documento: %s | Es soporte: %s | Estado: %s",
                move.name, move.l10n_co_edi_is_support_document, move.state
            )

            if move.l10n_co_edi_is_support_document and move.state == 'draft':
                previous_doc = move._get_previous_support_document()
                move.previous_support_doc_id = previous_doc
                move.previous_support_doc_dian_state = previous_doc.l10n_co_dian_state if previous_doc else False

                _logger.info(
                    "✅ [COMPUTE] Doc anterior encontrado: %s | Estado DIAN: %s",
                    previous_doc.name if previous_doc else 'NINGUNO',
                    previous_doc.l10n_co_dian_state if previous_doc else 'N/A'
                )
            else:
                move.previous_support_doc_id = False
                move.previous_support_doc_dian_state = False
                _logger.info("⏭️  [COMPUTE] No requiere cálculo (no es soporte o no está en borrador)")

    @api.depends('previous_support_doc_id', 'previous_support_doc_dian_state',
                 'support_doc_validation_override')
    def _compute_show_support_doc_warning(self):
        """Determina si mostrar advertencia de validación"""
        for move in self:
            show_warning = False

            if (move.l10n_co_edi_is_support_document
                and move.previous_support_doc_id
                and not move.support_doc_validation_override
                and move.company_id.support_doc_sequence_validation):

                dian_state = move.previous_support_doc_dian_state
                # Mostrar warning si no está aceptado o rechazado
                # if dian_state not in ['invoice_accepted', 'invoice_rejected']:
                if dian_state not in ['invoice_accepted']:
                    show_warning = True

            move.show_support_doc_warning = show_warning

    # ========== MÉTODOS DE VALIDACIÓN ==========

    def _is_support_document(self):
        """
        Determina si el documento es un documento soporte

        Usa el campo validado: l10n_co_edi_is_support_document
        Este campo es computed en el journal y se basa en:
        - journal.type == 'purchase'
        - journal.l10n_co_edi_dian_authorization_number existe

        Returns:
            bool: True si es documento soporte
        """
        self.ensure_one()
        is_support = bool(self.l10n_co_edi_is_support_document)
        _logger.info(
            "📋 [IS_SUPPORT] Documento %s | Journal: %s | Es soporte: %s",
            self.name, self.journal_id.name, is_support
        )
        return is_support

    def _get_previous_support_document(self):
        """
        Busca el documento soporte inmediatamente anterior en la secuencia

        Estrategia SIN usar name (para evitar asignar secuencia prematuramente):
        1. Mismo journal
        2. Mismo tipo (l10n_co_edi_is_support_document = True)
        3. Estado confirmado (state = 'posted')
        4. ID menor (último confirmado cronológicamente)

        Returns:
            account.move: Documento anterior o recordset vacío
        """
        self.ensure_one()

        _logger.info("🔎 [GET_PREVIOUS] Iniciando búsqueda para documento ID=%s, name=%s", self.id, self.name)

        # Dominio de búsqueda: Como l10n_co_edi_is_support_document no está stored,
        # buscamos usando el mismo journal que ya sabemos que es de documentos soporte
        # El journal solo se usa para documentos soporte si cumple las condiciones
        domain = [
            ('journal_id', '=', self.journal_id.id),
            ('move_type', '=', self.move_type),
            ('state', '=', 'posted'),
            ('id', '<', self.id if self.id else 999999999),  # IDs menores = documentos anteriores
        ]

        _logger.info(
            "🔍 [GET_PREVIOUS] Dominio: Journal=%s, Tipo=%s, Estado=posted, ID<%s",
            self.journal_id.name, self.move_type, self.id or 'NEW'
        )

        # Buscar el último documento confirmado (mayor ID de los anteriores)
        # Como estamos usando el mismo journal, todos los documentos ya son soportes
        previous_doc = self.search(domain, order='id desc', limit=1)

        if previous_doc:
            _logger.info(
                "✅ [GET_PREVIOUS] Documento anterior encontrado: %s (ID=%s, fecha=%s)",
                previous_doc.name, previous_doc.id, previous_doc.date
            )
            return previous_doc
        else:
            _logger.info("❌ [GET_PREVIOUS] No se encontró documento anterior (es el primero del diario)")
            return self.env['account.move']

    def _validate_previous_support_document_sent(self):
        """
        Valida que el documento anterior esté enviado a DIAN

        Estados válidos DIAN (campo l10n_co_dian_state):
        - 'invoice_accepted': Documento aceptado por DIAN ✅
        - 'invoice_rejected': Documento rechazado (permitimos continuar) ⚠️

        Estados que BLOQUEAN:
        - 'invoice_sending_failed': Fallo en envío ❌
        - 'invoice_pending': Pendiente de respuesta ❌
        - None/False: No enviado ❌

        Returns:
            dict: {
                'valid': bool,
                'level': 'error'|'warning'|'info',
                'message': str,
                'previous_doc': recordset,
                'previous_doc_number': str,
                'previous_doc_dian_state': str,
            }
        """
        self.ensure_one()

        _logger.info("🔐 [VALIDATE] Iniciando validación para documento: %s", self.name)

        previous_doc = self._get_previous_support_document()

        # Si no hay documento anterior, validación OK
        if not previous_doc:
            _logger.info("✅ [VALIDATE] No hay documento anterior, validación OK")
            return {
                'valid': True,
                'level': 'info',
                'message': _('No hay documento anterior para validar'),
                'previous_doc': self.env['account.move'],
                'previous_doc_number': '',
                'previous_doc_dian_state': '',
            }

        # Obtener estado DIAN del documento anterior
        dian_state = previous_doc.l10n_co_dian_state
        _logger.info(
            "🏷️  [VALIDATE] Documento anterior: %s | Estado DIAN: %s",
            previous_doc.name, dian_state or 'NO ENVIADO'
        )

        # Estados que permiten continuar
        valid_states = ['invoice_accepted']
        # También permitimos si fue rechazado (para no bloquear indefinidamente)
        
        # allowed_states = valid_states + ['invoice_rejected']
        allowed_states = valid_states

        if dian_state in allowed_states:
            _logger.info("✅ [VALIDATE] Estado DIAN válido, permitir continuar")
            state_label = dict(
                previous_doc._fields['l10n_co_dian_state'].selection
            ).get(dian_state, dian_state)

            return {
                'valid': True,
                'level': 'info',
                'message': _('Documento anterior %s enviado a DIAN (Estado: %s)') % (
                    previous_doc.name,
                    state_label
                ),
                'previous_doc': previous_doc,
                'previous_doc_number': previous_doc.name,
                'previous_doc_dian_state': dian_state,
            }
        else:
            # Estados problemáticos: sending_failed, pending, o None
            if dian_state:
                state_label = dict(
                    previous_doc._fields['l10n_co_dian_state'].selection
                ).get(dian_state, 'Estado desconocido')
            else:
                state_label = 'No enviado'

            _logger.warning(
                "❌ [VALIDATE] Estado DIAN inválido: %s | Bloquear confirmación",
                state_label
            )

            cuds = previous_doc.l10n_co_edi_cufe_cude_ref or 'Sin CUDS'

            return {
                'valid': False,
                'level': 'error',
                'message': _(
                    'No se puede confirmar el documento soporte \n\n'
                    '❌ El documento anterior %s aún no ha sido enviado correctamente a la DIAN.\n'
                    '📋 Estado actual: %s\n'
                    '💡 Por favor, envíe primero el documento %s a la DIAN.\n'
                    '   Puede hacerlo desde el botón "Enviar Documento Soporte a DIAN".'
                ) % (
                    previous_doc.name,
                    state_label,
                    previous_doc.name
                ),
                'previous_doc': previous_doc,
                'previous_doc_number': previous_doc.name,
                'previous_doc_dian_state': dian_state or '',
            }

    # ========== OVERRIDE DE MÉTODOS ==========

    def action_post(self):
        """
        Override del método de confirmación de facturas

        Ejecuta validación de secuencia ANTES de confirmar si:
        - Es un documento soporte (l10n_co_edi_is_support_document = True)
        - La validación está activa (company.support_doc_sequence_validation = True)
        - No hay bypass manual (support_doc_validation_override = False)
        """
        _logger.info("="*80)
        _logger.info("🚀 [ACTION_POST] Iniciando confirmación de documentos")

        for move in self:
            _logger.info("📄 [ACTION_POST] Procesando documento ID=%s, name=%s", move.id, move.name)

            # Solo validar documentos soporte
            if move._is_support_document():
                _logger.info("✅ [ACTION_POST] Es documento soporte, verificar configuración")

                # Verificar si validación está activa en la compañía
                validation_active = move.company_id.support_doc_sequence_validation
                validation_mode = move.company_id.support_doc_validation_mode
                _logger.info(
                    "⚙️  [ACTION_POST] Configuración: Validación=%s | Modo=%s",
                    validation_active, validation_mode
                )

                if validation_active:
                    _logger.info("🔒 [ACTION_POST] Validación activa, verificar bypass")

                    # Permitir bypass manual (solo usuarios con permiso)
                    if not move.support_doc_validation_override:
                        _logger.info("🔐 [ACTION_POST] Sin bypass, ejecutar validación")

                        # Ejecutar validación
                        validation_result = move._validate_previous_support_document_sent()

                        _logger.info(
                            "📊 [ACTION_POST] Resultado validación: valid=%s | level=%s",
                            validation_result['valid'], validation_result['level']
                        )

                        if not validation_result['valid']:
                            # Decidir acción según configuración de la compañía
                            if validation_mode == 'block':
                                # Modo BLOQUEAR: Lanzar error y no permitir confirmar
                                _logger.error(
                                    "🚫 [ACTION_POST] BLOQUEANDO confirmación de %s: "
                                    "documento anterior %s no enviado a DIAN (estado: %s)",
                                    move.name,
                                    validation_result.get('previous_doc_number', 'N/A'),
                                    validation_result.get('previous_doc_dian_state', 'N/A')
                                )
                                raise UserError(validation_result['message'])
                            else:
                                # Modo ADVERTIR: Solo loguear y permitir continuar
                                _logger.warning(
                                    "⚠️  [ACTION_POST] ADVERTENCIA: Documento soporte %s confirmado sin enviar anterior %s. "
                                    "Estado DIAN anterior: %s",
                                    move.name,
                                    validation_result.get('previous_doc_number', 'N/A'),
                                    validation_result.get('previous_doc_dian_state', 'N/A')
                                )
                        else:
                            _logger.info("✅ [ACTION_POST] Validación exitosa, permitir confirmación")
                    else:
                        # Bypass activado - loguear para auditoría
                        _logger.warning(
                            "🔓 [ACTION_POST] BYPASS activado por usuario %s para documento %s",
                            self.env.user.name,
                            move.name
                        )
                else:
                    _logger.info("⏭️  [ACTION_POST] Validación desactivada en compañía, omitir")
            else:
                _logger.info("⏭️  [ACTION_POST] No es documento soporte, omitir validación")

        _logger.info("✅ [ACTION_POST] Pre-validación completa, ejecutar super().action_post()")
        _logger.info("="*80)

        # Continuar con proceso normal de confirmación
        return super().action_post()

    # ========== MÉTODOS AUXILIARES ==========

    def action_view_previous_support_document(self):
        """Acción para abrir el documento soporte anterior"""
        self.ensure_one()

        previous_doc = self.previous_support_doc_id
        if not previous_doc:
            raise UserError(_('No hay documento anterior para mostrar'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Documento Soporte Anterior - %s') % previous_doc.name,
            'res_model': 'account.move',
            'res_id': previous_doc.id,
            'view_mode': 'form',
            'target': 'current',
        }
