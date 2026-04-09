# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _  # type: ignore
from odoo.exceptions import UserError  # type: ignore

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    statement_email_opt_out = fields.Boolean(
        string='No enviar estado de cuenta',
        help='Si está activo, este cliente recibirá correos automáticos de cartera.'
    )

    last_statement_sent_date = fields.Datetime(
        string='Último envío de estado de cuenta',
        readonly=True
    )

    statement_recipient_email = fields.Char(
        string='Correo para estado de cuenta',
        help='Si se define, este correo tendrá prioridad sobre el email principal del contacto.'
    )

    def cron_send_customer_statements(self):
        _logger.info("\n\n Llegaste perra \n\n")

