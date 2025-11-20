# -*- coding: utf-8 -*-
import logging
from datetime import date
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    dian_alert_html = fields.Html(string="DIAN Alert")
