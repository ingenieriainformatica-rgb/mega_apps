import logging
from lxml import etree
from odoo import models

_logger = logging.getLogger(__name__)


def _is_broken_studio_1106(arch_db: str) -> bool:
    if not arch_db:
        return False
    try:
        root = etree.fromstring(arch_db.encode("utf-8"))
    except Exception:
        # Malformed XML -> consider broken
        return True

    # Check xpath nodes that target the transient Studio button name '1106'
    for xp in root.xpath("//xpath[@expr]"):
        expr = (xp.get("expr") or "").replace("&quot;", '"').replace("&#39;", "'")
        if "header/button" in expr and "@name" in expr and "1106" in expr:
            return True

    # Also guard literal button targets (rare in inherited views)
    for _btn in root.xpath(".//header/button[@name='1106'] | .//header/button[@name=\"1106\"]"):
        return True

    return False


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    def _register_hook(self):
        res = super()._register_hook()
        try:
            self._disable_broken_payment_views()
        except Exception as e:
            _logger.warning("realnet_pagos_consecutivos: failed to disable broken Studio views at startup: %s", e)
        return res

    def _disable_broken_payment_views(self):
        # Only target inherited account.payment views, active ones
        views = self.search([
            ("model", "=", "account.payment"),
            ("inherit_id", "!=", False),
            ("active", "=", True),
        ])
        to_disable = self.browse()
        for v in views:
            if _is_broken_studio_1106(v.arch_db or ""):
                to_disable |= v
        if to_disable:
            to_disable.write({"active": False})
            _logger.info(
                "realnet_pagos_consecutivos: disabled %d broken Studio inherited views on account.payment (button[@name='1106']).",
                len(to_disable),
            )
