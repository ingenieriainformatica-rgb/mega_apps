import logging
from odoo import models, fields, api  #type: ignore

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    # Campo booleano para indicar si el diario es visible solo para ciertos usuarios
    visible_journal = fields.Boolean(string="Visible solo para usuarios especiales", default=False)
