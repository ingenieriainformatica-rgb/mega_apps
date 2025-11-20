# -*- coding: utf-8 -*-
import logging
from odoo import api, models, _

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model_create_multi
    def create(self, vals_list):
        """
        Fuerza que el campo 'name' se guarde siempre en mayúscula al crear.
        """
        for vals in vals_list:
            name = vals.get("name")
            if name:
                vals["name"] = name.upper()
        partners = super().create(vals_list)
        _logger.info("Se crearon %s contactos con nombre en mayúscula.", len(partners))
        return partners

    def write(self, vals):
        """
        Fuerza que el campo 'name' se guarde siempre en mayúscula al modificar.
        """
        name = vals.get("name")
        if name:
            vals["name"] = name.upper()
        res = super().write(vals)
        _logger.info("Actualizados %s contactos con nombre en mayúscula.", len(self))
        return res

    @api.model
    def action_update_names_uppercase(self):
        """
        Actualiza todos los partners a MAYÚSCULA.
        Params:
            company_id: int/False -> limita por compañía si viene un ID
            include_archived: bool -> si True, considera archivados (active_test=False)
        """
        ctx = dict(self.env.context or {})

        Partner = self.with_context(ctx).sudo()

        domain = []

        partners = Partner.search(domain)
        updated = 0

        # Uso de ORM para respetar write_uid/write_date y posibles extensiones
        for p in partners:
            if p.name:
                upper = p.name.upper()
                if p.name != upper:
                    p.write({"name": upper})
                    updated += 1

        # Notificación en UI
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Actualización completada"),
                "message": _("Se actualizaron %s contactos a mayúsculas.") % updated,
                "type": "success",
                "sticky": False,
            },
        }
