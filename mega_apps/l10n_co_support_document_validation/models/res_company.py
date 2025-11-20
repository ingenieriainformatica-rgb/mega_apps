# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    support_doc_sequence_validation = fields.Boolean(
        string='Validar Secuencia de Documentos Soporte',
        default=True,
        help='Si está activo, el sistema validará que los documentos soporte se envíen '
             'a la DIAN en orden secuencial antes de permitir confirmar nuevos documentos.'
    )

    support_doc_validation_mode = fields.Selection(
        selection=[
            ('block', 'Bloquear Confirmación'),
            ('warn', 'Solo Advertir'),
        ],
        string='Modo de Validación',
        default='block',
        help='Define el comportamiento cuando un documento anterior no ha sido enviado:\n'
             '• Bloquear: No permite confirmar la factura y muestra error\n'
             '• Advertir: Permite confirmar pero registra advertencia en log'
    )
