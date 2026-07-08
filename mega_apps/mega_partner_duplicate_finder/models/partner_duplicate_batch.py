# -*- coding: utf-8 -*-
import re
import unicodedata

from odoo import _, api, fields, models


class PartnerDuplicateBatch(models.Model):
    _name = "partner.duplicate.batch"
    _description = "Lote de búsqueda de contactos repetidos"
    _order = "id desc"

    name = fields.Char(
        string="Referencia", required=True, copy=False, default=lambda self: _("New")
    )
    user_id = fields.Many2one(
        "res.users",
        string="Ejecutado por",
        default=lambda self: self.env.user,
        readonly=True,
    )
    search_type = fields.Selection(
        [
            ("vat", "Documento"),
            ("name", "Nombre"),
            ("all", "Todos"),
        ],
        string="Tipo de búsqueda",
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("done", "Finalizado"),
        ],
        string="Estado",
        default="draft",
        required=True,
        readonly=True,
    )
    group_ids = fields.One2many(
        "partner.duplicate.group", "batch_id", string="Grupos encontrados"
    )
    total_groups = fields.Integer(
        string="Total grupos", compute="_compute_totals", store=True
    )
    total_contacts = fields.Integer(
        string="Total contactos", compute="_compute_totals", store=True
    )

    @api.depends("group_ids.contact_count")
    def _compute_totals(self):
        for batch in self:
            batch.total_groups = len(batch.group_ids)
            batch.total_contacts = sum(batch.group_ids.mapped("contact_count"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("partner.duplicate.batch")
                    or _("New")
                )
        return super().create(vals_list)

    # ---------------------------------------------------------------------
    # Normalización
    # ---------------------------------------------------------------------
    @staticmethod
    def _normalize_vat(value):
        if not value:
            return False
        value = value.upper()
        value = re.sub(r"[\s.\-]", "", value)
        return value or False

    @staticmethod
    def _normalize_name(value):
        if not value:
            return False
        value = value.strip().upper()
        value = unicodedata.normalize("NFKD", value)
        value = "".join(c for c in value if not unicodedata.combining(c))
        value = re.sub(r"[^A-Z0-9\s]", "", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value or False

    # ---------------------------------------------------------------------
    # Búsqueda
    # ---------------------------------------------------------------------
    def _prepare_line_vals(self, partner):
        return {
            "partner_id": partner.id,
            "name_snapshot": partner.name,
            "vat_snapshot": partner.vat,
            "email_snapshot": partner.email,
            "phone_snapshot": partner.phone,
            "mobile_snapshot": partner.mobile,
            "city_snapshot": partner.city,
            "company_id_snapshot": partner.company_id.id,
            "parent_id_snapshot": partner.parent_id.id,
            "active_snapshot": partner.active,
        }

    def _run_search(self, match_type):
        """Agrupa res.partner por vat/name normalizado y crea los grupos
        con 2 o más contactos que aún no existan en este lote."""
        self.ensure_one()
        normalize = (
            self._normalize_vat if match_type == "vat" else self._normalize_name
        )
        field_name = "vat" if match_type == "vat" else "name"

        partners = self.env["res.partner"].with_context(active_test=False).search([])

        buckets = {}
        raw_values = {}
        for partner in partners:
            raw = partner[field_name]
            normalized = normalize(raw)
            if not normalized:
                continue
            buckets.setdefault(normalized, self.env["res.partner"])
            buckets[normalized] |= partner
            raw_values.setdefault(normalized, raw)

        existing_normalized = set(
            self.group_ids.filtered(lambda g: g.match_type == match_type).mapped(
                "normalized_value"
            )
        )

        group_vals_list = []
        for normalized, partner_group in buckets.items():
            if len(partner_group) < 2:
                continue
            if normalized in existing_normalized:
                continue
            group_vals_list.append(
                {
                    "batch_id": self.id,
                    "match_type": match_type,
                    "match_value": raw_values[normalized],
                    "normalized_value": normalized,
                    "line_ids": [
                        (0, 0, self._prepare_line_vals(partner))
                        for partner in partner_group
                    ],
                }
            )

        if group_vals_list:
            self.env["partner.duplicate.group"].create(group_vals_list)

    def action_search_vat(self):
        for batch in self:
            batch.search_type = "vat"
            batch._run_search("vat")
            batch.state = "done"

    def action_search_name(self):
        for batch in self:
            batch.search_type = "name"
            batch._run_search("name")
            batch.state = "done"

    def action_search_all(self):
        for batch in self:
            batch.search_type = "all"
            batch._run_search("vat")
            batch._run_search("name")
            batch.state = "done"
