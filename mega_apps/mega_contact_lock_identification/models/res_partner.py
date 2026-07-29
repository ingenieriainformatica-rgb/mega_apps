# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

CO_COUNTRY_XML_ID = "base.co"
CO_PERSON_IDENTIFICATION_XML_ID = "l10n_co.national_citizen_id"
CO_COMPANY_IDENTIFICATION_XML_ID = "l10n_co.rut"

CORRECTION_GROUP_XML_ID = "mega_contact_lock_identification.group_contact_identification_correction"
CORRECTION_WIZARD_MODEL = "mega.contact.identification.correction"
CORRECTION_CTX_KEY = "mega_identification_correction_wizard_id"

IDENTIFICATION_FIELDS = ("vat", "l10n_latam_identification_type_id")


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Los contactos nuevos suelen operar en Colombia; precargar el pais de la
    # compania activa evita el candado "pais oculto hasta tener vat" sin
    # tocar ningun registro existente (un default solo aplica en create()).
    country_id = fields.Many2one(default=lambda self: self.env.company.country_id)

    # ------------------------------------------------------------------
    # Fase 1: onchange guiado por pais, usando XML ID en vez de ilike
    # ------------------------------------------------------------------

    @api.onchange("company_type", "is_company", "country_id")
    def _onchange_set_identification_type_for_person(self):
        co = self.env.ref(CO_COUNTRY_XML_ID, raise_if_not_found=False)
        if not co:
            return

        person_type = self.env.ref(CO_PERSON_IDENTIFICATION_XML_ID, raise_if_not_found=False)
        company_type_id = self.env.ref(CO_COMPANY_IDENTIFICATION_XML_ID, raise_if_not_found=False)

        for rec in self:
            # Solo se autoasigna tipo colombiano si el contacto es colombiano.
            # Si no hay pais todavia, no se asume nada (se deja que el
            # usuario elija pais primero).
            if rec.country_id != co:
                continue

            is_person = rec.company_type == "person" or not rec.is_company
            target_type = person_type if is_person else company_type_id
            if not target_type:
                continue

            current_type = rec.l10n_latam_identification_type_id
            if current_type == target_type:
                continue
            # Si ya tiene un tipo colombiano de la MISMA categoria (ej.
            # Cedula de extranjeria o PEP cuando es persona, is_vat=False al
            # igual que la cedula) se respeta la eleccion previa. Pero si es
            # de la categoria contraria (ej. quedo en NIT porque antes era
            # Empresa y ahora es Persona), se corrige: no tiene sentido
            # dejar un NIT en una persona ni una cedula en una empresa.
            if current_type and current_type.country_id == co and bool(current_type.is_vat) == (not is_person):
                continue

            rec.l10n_latam_identification_type_id = target_type

    # ------------------------------------------------------------------
    # Fase 2: validacion de negocio (no se aplica en create/write general)
    # ------------------------------------------------------------------

    def _check_mega_commercial_identification(self, action_label):
        """Valida que el tercero comercial colombiano tenga identificacion.

        Siempre se valida sobre ``commercial_partner_id``, nunca sobre un
        contacto hijo/direccion. No debe llamarse desde create()/write():
        se invoca solo en los puntos de negocio donde la identificacion ya
        es obligatoria (confirmar venta, contabilizar factura).
        """
        co = self.env.ref(CO_COUNTRY_XML_ID, raise_if_not_found=False)
        nit_type = self.env.ref(CO_COMPANY_IDENTIFICATION_XML_ID, raise_if_not_found=False)

        for partner in self:
            commercial = partner.commercial_partner_id
            if not commercial.country_id:
                raise UserError(_(
                    "Defina el país de %(partner)s antes de %(action)s.",
                    partner=commercial.display_name,
                    action=action_label,
                ))

            if not co or commercial.country_id != co:
                # Reglas colombianas no aplican a contactos extranjeros.
                continue

            vat = (commercial.vat or "").strip()
            id_type = commercial.l10n_latam_identification_type_id

            if commercial.is_company:
                if not nit_type or id_type != nit_type:
                    raise UserError(_(
                        "Las empresas colombianas deben utilizar el tipo de identificación "
                        "NIT. Revise el contacto %(partner)s antes de %(action)s.",
                        partner=commercial.display_name,
                        action=action_label,
                    ))
            elif not id_type:
                raise UserError(_(
                    "Las personas colombianas deben tener un tipo de identificación "
                    "válido. Revise el contacto %(partner)s antes de %(action)s.",
                    partner=commercial.display_name,
                    action=action_label,
                ))

            if not vat:
                raise UserError(_(
                    "El contacto %(partner)s no tiene número de identificación. "
                    "Complételo antes de %(action)s.",
                    partner=commercial.display_name,
                    action=action_label,
                ))

    def _mega_has_commercial_history(self):
        """True si el contacto ya tiene actividad que hace sensible cambiar
        su identificacion sin trazabilidad (ventas, compras, contabilidad,
        pagos, o si es un contacto tecnico de usuario/empleado/compania)."""
        self.ensure_one()
        env = self.env
        if env["res.company"].sudo().search_count([("partner_id", "=", self.id)], limit=1):
            return True
        if env["res.users"].sudo().search_count([("partner_id", "=", self.id)], limit=1):
            return True
        if "hr.employee" in env and env["hr.employee"].sudo().search_count(
            [("work_contact_id", "=", self.id)], limit=1
        ):
            return True
        if env["account.move"].sudo().search_count(
            [("partner_id", "=", self.id), ("state", "=", "posted")], limit=1
        ):
            return True
        if "sale.order" in env and env["sale.order"].sudo().search_count(
            [("partner_id", "=", self.id), ("state", "=", "sale")], limit=1
        ):
            return True
        if "purchase.order" in env and env["purchase.order"].sudo().search_count(
            [("partner_id", "=", self.id), ("state", "in", ("purchase", "done"))], limit=1
        ):
            return True
        if "account.payment" in env and env["account.payment"].sudo().search_count(
            [("partner_id", "=", self.id), ("state", "in", ("in_process", "paid"))], limit=1
        ):
            return True
        return False

    # ------------------------------------------------------------------
    # Fase 3: proteccion backend sobre cambios de identificacion
    # ------------------------------------------------------------------

    def write(self, vals):
        if not self.env.su and any(f in vals for f in IDENTIFICATION_FIELDS):
            self._check_mega_identification_change_allowed(vals)
        return super().write(vals)

    def _check_mega_identification_change_allowed(self, vals):
        wizard_id = self.env.context.get(CORRECTION_CTX_KEY)
        wizard = None
        if wizard_id and CORRECTION_WIZARD_MODEL in self.env:
            wizard = self.env[CORRECTION_WIZARD_MODEL].sudo().browse(wizard_id).exists()

        has_group = self.env.user.has_group(CORRECTION_GROUP_XML_ID)

        for partner in self:
            new_vat = vals["vat"] if "vat" in vals else partner.vat
            new_type_id = (
                vals["l10n_latam_identification_type_id"]
                if "l10n_latam_identification_type_id" in vals
                else partner.l10n_latam_identification_type_id.id
            )
            if new_vat == partner.vat and new_type_id == partner.l10n_latam_identification_type_id.id:
                continue  # sin cambio real: no bloquear

            if not partner._mega_has_commercial_history():
                continue  # sin historial: edicion libre, comportamiento estandar

            authorized = bool(
                wizard
                and has_group
                and wizard.partner_id == partner
                and wizard.create_uid == self.env.user
                and (wizard.reason or "").strip()
            )
            if not authorized:
                raise UserError(_(
                    "Este contacto tiene movimientos asociados (ventas, compras, facturas, "
                    "pagos, usuario o empleado vinculado). Utilice la acción "
                    "'Corregir identificación' para modificarlo con la debida "
                    "autorización y trazabilidad."
                ))

    def action_open_mega_identification_correction(self):
        self.ensure_one()
        if not self.env.user.has_group(CORRECTION_GROUP_XML_ID):
            raise UserError(_("No tiene permisos para corregir la identificación."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Corregir identificación"),
            "res_model": CORRECTION_WIZARD_MODEL,
            "view_mode": "form",
            "target": "new",
            "context": {"default_partner_id": self.id},
        }
