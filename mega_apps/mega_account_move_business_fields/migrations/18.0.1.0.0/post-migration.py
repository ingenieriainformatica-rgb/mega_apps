# -*- coding: utf-8 -*-
from odoo.addons.mega_account_move_business_fields.hooks import (
    sync_mega_concepto_from_studio,
)


def migrate(cr, version):
    """Se ejecuta solo cuando el módulo ya estaba instalado y se actualiza
    (no en una instalación limpia, ver post_init_hook en __init__.py)."""
    sync_mega_concepto_from_studio(cr)
