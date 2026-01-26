# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models  #type: ignore

_logger = logging.getLogger(__name__)


class ResPartnerCustom(models.Model):
    _inherit = "res.partner"

    is_advisor = fields.Boolean(
        string="Es asesor",
        help="Si está activo, este contacto podrá seleccionarse como asesor en las Órdenes de Venta.",
        default=False,
        required=True
    )
