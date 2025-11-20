# -*- coding: utf-8 -*-

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    support_doc_sequence_validation = fields.Boolean(
        string='Validar Secuencia de Documentos Soporte',
        related='company_id.support_doc_sequence_validation',
        readonly=False,
        help='Activa la validación de secuencia para documentos soporte. '
             'Cuando está activo, no se podrán confirmar documentos soporte '
             'si el documento anterior no ha sido enviado a la DIAN.'
    )

    support_doc_validation_mode = fields.Selection(
        string='Modo de Validación',
        related='company_id.support_doc_validation_mode',
        readonly=False,
        help='Define si bloquear o solo advertir cuando falte enviar documento anterior'
    )
