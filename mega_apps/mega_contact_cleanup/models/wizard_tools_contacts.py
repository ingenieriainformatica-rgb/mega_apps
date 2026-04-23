# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _  # type: ignore
from odoo.exceptions import UserError  # type: ignore

_logger = logging.getLogger(__name__)


class ContactMenuWizard(models.TransientModel):
    _name = "contact.menu.wizard"
    _description = "Tools for cleaning up contact information"

    candidate_count = fields.Integer(
        string="Contactos candidatos",
        readonly=True,
    )

    warning_message = fields.Html(
        string="Mensaje",
        readonly=True,
        compute="_compute_warning_message",
    )

    date_from = fields.Datetime(string="Fecha creación desde")
    date_to = fields.Datetime(string="Fecha creación hasta")
    limit_records = fields.Integer(string="Límite", default=500)

    @api.depends("candidate_count")
    def _compute_warning_message(self):
        for wizard in self:
            wizard.warning_message = _(
                "<b>Se eliminarán %s contactos</b> que cumplan todas las validaciones: "
                "sin usuario, sin facturación, sin compras, sin ventas, sin leads, "
                "sin empleados asociados, sin fondos de cesantías y sin EPS asociada."
            ) % wizard.candidate_count

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        vals.setdefault("limit_records", 500)
        vals["candidate_count"] = self._get_cleanup_candidate_count_for_vals(vals)
        return vals

    @api.onchange("date_from", "date_to", "limit_records")
    def _onchange_recompute_candidate_count(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                wizard.candidate_count = 0
                return {
                    "warning": {
                        "title": _("Rango de fechas inválido"),
                        "message": _("La fecha inicial no puede ser mayor que la fecha final."),
                    }
                }

            wizard.candidate_count = wizard._get_cleanup_candidate_count()

    def _get_cleanup_domain(self):
        self.ensure_one()

        company_partner_ids = self.env["res.company"].sudo().search([]).mapped("partner_id").ids

        domain = [
            ("active", "=", True),
            ("id", "not in", company_partner_ids),
            ("user_ids", "=", False),
            ("child_ids", "=", False),
        ]

        if self.date_from:
            domain.append(("create_date", ">=", self.date_from))

        if self.date_to:
            domain.append(("create_date", "<=", self.date_to))

        return domain

    @api.model
    def _get_cleanup_domain_from_vals(self, vals):
        company_partner_ids = self.env["res.company"].sudo().search([]).mapped("partner_id").ids

        domain = [
            ("active", "=", True),
            ("id", "not in", company_partner_ids),
            ("user_ids", "=", False),
            ("child_ids", "=", False),
        ]

        date_from = vals.get("date_from")
        date_to = vals.get("date_to")

        if date_from:
            domain.append(("create_date", ">=", date_from))

        if date_to:
            domain.append(("create_date", "<=", date_to))

        return domain

    def _partner_has_employee_relation(self, partner):
        if "hr.employee" not in self.env:
            return False

        employee_model = self.env["hr.employee"].sudo()
        domain_parts = []

        if "work_contact_id" in employee_model._fields:
            domain_parts.append(("work_contact_id", "=", partner.id))

        if "address_home_id" in employee_model._fields:
            domain_parts.append(("address_home_id", "=", partner.id))

        if "address_id" in employee_model._fields:
            domain_parts.append(("address_id", "=", partner.id))

        if not domain_parts:
            return False

        if len(domain_parts) == 1:
            domain = domain_parts
        else:
            domain = ["|"] * (len(domain_parts) - 1) + domain_parts

        return bool(employee_model.search_count(domain))

    def _partner_has_cesantias_fund_relation(self, partner):
        self.env.cr.execute("""
            SELECT 1
            FROM l10n_co_nomina_cesantias_fund
            WHERE partner_id = %s
            LIMIT 1
        """, (partner.id,))
        return bool(self.env.cr.fetchone())

    def _partner_has_eps_relation(self, partner):
        self.env.cr.execute("""
            SELECT 1
            FROM l10n_co_nomina_eps
            WHERE partner_id = %s
            LIMIT 1
        """, (partner.id,))
        return bool(self.env.cr.fetchone())

    def _partner_passes_all_cleanup_rules(self, partner):
        reasons = []

        has_account_move = bool(self.env["account.move"].sudo().search_count([
            ("partner_id", "=", partner.id),
            ("state", "!=", "cancel"),
        ]))
        if has_account_move:
            reasons.append("Tiene facturación o movimientos contables")

        has_purchase = bool(self.env["purchase.order"].sudo().search_count([
            ("partner_id", "=", partner.id),
        ]))
        if has_purchase:
            reasons.append("Tiene compras")

        has_sale = bool(self.env["sale.order"].sudo().search_count([
            ("partner_id", "=", partner.id),
        ]))
        if has_sale:
            reasons.append("Tiene ventas")

        has_lead = bool(self.env["crm.lead"].sudo().search_count([
            ("partner_id", "=", partner.id),
        ]))
        if has_lead:
            reasons.append("Tiene leads u oportunidades")

        if self._partner_has_cesantias_fund_relation(partner):
            reasons.append("Está asociado a fondo de cesantías")

        if self._partner_has_eps_relation(partner):
            reasons.append("Está asociado a EPS")

        if self._partner_has_employee_relation(partner):
            reasons.append("Está asociado a empleado")

        return (len(reasons) == 0, reasons)

    def _get_cleanup_candidates(self):
        self.ensure_one()

        Partner = self.env["res.partner"].sudo()
        partners = Partner.search(
            self._get_cleanup_domain(),
            order="create_date asc, id asc",
            limit=self.limit_records or None,
        )

        valid_partners = self.env["res.partner"]

        for partner in partners:
            passes, reasons = self._partner_passes_all_cleanup_rules(partner)
            if passes:
                valid_partners |= partner
            else:
                _logger.info(
                    "Partner %s (%s) excluded from cleanup. Reasons: %s",
                    partner.id,
                    partner.name or "",
                    ", ".join(reasons),
                )

        return valid_partners

    @api.model
    def _get_cleanup_candidates_from_vals(self, vals):
        Partner = self.env["res.partner"].sudo()
        limit_records = vals.get("limit_records") or 500

        partners = Partner.search(
            self._get_cleanup_domain_from_vals(vals),
            order="create_date asc, id asc",
            limit=limit_records,
        )

        valid_partners = self.env["res.partner"]
        wizard = self.new(vals)

        for partner in partners:
            passes, _reasons = wizard._partner_passes_all_cleanup_rules(partner)
            if passes:
                valid_partners |= partner

        return valid_partners

    def _get_cleanup_candidate_count(self):
        self.ensure_one()
        return len(self._get_cleanup_candidates())

    @api.model
    def _get_cleanup_candidate_count_for_vals(self, vals):
        return len(self._get_cleanup_candidates_from_vals(vals))

    def action_refresh_candidate_count(self):
        self.ensure_one()
        self.candidate_count = self._get_cleanup_candidate_count()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Limpieza de contactos"),
                "message": _("Se recalculó el total de candidatos: %s") % self.candidate_count,
                "type": "info",
                "sticky": False,
            },
        }

    def action_confirm(self):
        self.ensure_one()

        candidates = self._get_cleanup_candidates()
        total = len(candidates)

        if not total:
            raise UserError(_("No se encontraron contactos candidatos para eliminar con los filtros actuales."))

        deleted_count = 0
        skipped_count = 0
        skipped_partners = []

        _logger.info(
            "Contact cleanup: found %s candidate contacts | date_from=%s | date_to=%s | limit=%s",
            total,
            self.date_from,
            self.date_to,
            self.limit_records,
        )

        for partner in candidates:
            partner_id = partner.id
            partner_name = partner.name or partner.email or f"Partner {partner_id}"

            try:
                with self.env.cr.savepoint():
                    _logger.info(
                        "Trying to delete partner ID %s - %s",
                        partner_id,
                        partner_name,
                    )

                    partner.unlink()
                    deleted_count += 1

                    _logger.info(
                        "Deleted partner ID %s - %s",
                        partner_id,
                        partner_name,
                    )

            except Exception as e:
                skipped_count += 1
                skipped_partners.append(f"[{partner_id}] {partner_name}")
                _logger.warning(
                    "Could not delete partner ID %s - %s. Error: %s",
                    partner_id,
                    partner_name,
                    str(e),
                )

        if skipped_partners:
            _logger.warning(
                "Skipped partners during cleanup:\n%s",
                "\n".join(skipped_partners)
            )

        message = _(
            "Eliminados: %(deleted)s | Omitidos: %(skipped)s"
        ) % {
            "deleted": deleted_count,
            "skipped": skipped_count,
        }

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Limpieza de contactos"),
                "message": message,
                "type": "warning" if skipped_count else "success",
                "sticky": True,
            },
        }
