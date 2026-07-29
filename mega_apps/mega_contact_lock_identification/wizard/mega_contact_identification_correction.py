# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

GROUP_XML_ID = "mega_contact_lock_identification.group_contact_identification_correction"
CTX_KEY = "mega_identification_correction_wizard_id"

# Estados DIAN que indican que ya se intento/logro enviar el documento a la
# DIAN (ver l10n_co_dian.models.account_move: l10n_co_dian_state).
DIAN_SENT_STATES = ("invoice_pending", "invoice_accepted")


class MegaContactIdentificationCorrection(models.TransientModel):
    _name = "mega.contact.identification.correction"
    _description = "Corrección controlada de identificación de contacto"

    partner_id = fields.Many2one("res.partner", required=True, readonly=True)

    current_identification_type_id = fields.Many2one(
        "l10n_latam.identification.type", related="partner_id.l10n_latam_identification_type_id",
        string="Tipo actual", readonly=True,
    )
    current_vat = fields.Char(related="partner_id.vat", string="Número actual", readonly=True)

    new_identification_type_id = fields.Many2one(
        "l10n_latam.identification.type", required=True, string="Nuevo tipo de identificación",
    )
    new_vat = fields.Char(required=True, string="Nuevo número de identificación")
    reason = fields.Text(required=True, string="Motivo de la corrección")

    company_partner_warning = fields.Char(compute="_compute_warnings")
    dian_warning = fields.Char(compute="_compute_warnings")
    merge_warning = fields.Char(compute="_compute_warnings")

    @api.depends("partner_id")
    def _compute_warnings(self):
        for wizard in self:
            wizard.company_partner_warning = wizard._get_company_partner_warning()
            wizard.dian_warning = wizard._get_dian_warning()
            wizard.merge_warning = wizard._get_merge_proposal_warning()

    def _get_company_partner_warning(self):
        self.ensure_one()
        if not self.partner_id:
            return False
        if self.env["res.company"].sudo().search_count([("partner_id", "=", self.partner_id.id)], limit=1):
            return _(
                "Este contacto es la compañía del sistema. Su identificación debe "
                "modificarse desde Ajustes de la Compañía, no desde este asistente."
            )
        return False

    def _get_dian_warning(self):
        """Advierte si el contacto tiene documentos DIAN ya enviados/aceptados.
        No bloquea: cambiar el maestro no modifica XML/CUFE ya emitidos, pero
        el usuario autorizado debe saberlo antes de confirmar."""
        self.ensure_one()
        if not self.partner_id or "l10n_co_dian_state" not in self.env["account.move"]._fields:
            return False
        has_dian_docs = self.env["account.move"].sudo().search_count([
            ("commercial_partner_id", "=", self.partner_id.id),
            ("l10n_co_dian_state", "in", DIAN_SENT_STATES),
        ], limit=1)
        if has_dian_docs:
            return _(
                "Este contacto tiene documentos electrónicos DIAN ya enviados o aceptados. "
                "Corregir la identificación NO modifica los XML/CUFE ya emitidos ante la DIAN. "
                "Proceda solo si tiene autorización para ello."
            )
        return False

    def _get_merge_proposal_warning(self):
        """No depende ni importa mega_partner_merge_by_vat: solo consulta el
        modelo si esta registrado en el entorno (instalado)."""
        self.ensure_one()
        if not self.partner_id or "partner.merge.proposal.line" not in self.env:
            return False
        pending = self.env["partner.merge.proposal.line"].sudo().search_count([
            ("partner_id", "=", self.partner_id.id),
            ("proposal_id.state", "=", "pending"),
        ], limit=1)
        if pending:
            return _(
                "Este contacto tiene una propuesta de fusión pendiente en el módulo de "
                "fusión de contactos. Revísela antes de corregir la identificación."
            )
        return False

    def action_confirm(self):
        self.ensure_one()

        if not self.env.user.has_group(GROUP_XML_ID):
            raise AccessError(_("No tiene permisos para corregir la identificación."))

        if not (self.reason or "").strip():
            raise UserError(_("Debe indicar un motivo para la corrección."))

        if self._get_company_partner_warning():
            raise UserError(_(
                "Este contacto es la compañía del sistema. Modifique su identificación "
                "desde Ajustes de la Compañía."
            ))

        old_type_name = self.current_identification_type_id.name or _("(sin tipo)")
        old_vat = self.current_vat or _("(vacío)")

        self.partner_id.with_context(**{CTX_KEY: self.id}).write({
            "vat": self.new_vat,
            "l10n_latam_identification_type_id": self.new_identification_type_id.id,
        })

        lines = [
            _("Corrección de identificación autorizada."),
            _("Tipo anterior: %s", old_type_name),
            _("VAT anterior: %s", old_vat),
            _("Tipo nuevo: %s", self.new_identification_type_id.name),
            _("VAT nuevo: %s", self.new_vat),
            _("Motivo: %s", self.reason),
            _("Usuario: %s", self.env.user.name),
            _("Fecha: %s", fields.Datetime.context_timestamp(self, fields.Datetime.now())),
        ]
        body = Markup("<br/>").join(Markup("{}").format(line) for line in lines)
        self.partner_id.message_post(body=body)

        return {"type": "ir.actions.act_window_close"}
