# -*- coding: utf-8 -*-

import logging

from markupsafe import Markup
from odoo import models  # type: ignore
from odoo.exceptions import UserError  # type: ignore


_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def _stage_is_won(self, stage) -> bool:
        return bool(
            stage
            and "is_won" in stage._fields
            and stage.is_won
        )

    def _is_whatsapp_terminal_lead(self) -> bool:
        self.ensure_one()

        if "active" in self._fields and not self.active:
            return True

        if self._stage_is_won(self.stage_id):
            return True

        return False

    def _target_state_is_terminal(self, vals: dict) -> bool:
        self.ensure_one()

        target_active = vals.get("active", self.active)

        if not target_active:
            return True

        target_stage = self.stage_id

        if "stage_id" in vals and vals.get("stage_id"):
            target_stage = self.env["crm.stage"].browse(vals["stage_id"])

        return self._stage_is_won(target_stage)

    def _prevent_reopening_closed_whatsapp_leads(self, vals: dict) -> None:
        """
        Evita que un lead de WhatsApp ya cerrado vuelva a una etapa abierta.

        Regla:
        - Si el lead tiene una sesión WhatsApp cerrada en done,
          no debe volver a Nuevo/Calificado.
        - Si el cliente vuelve a escribir, debe crear nueva sesión y nuevo lead.
        """
        if not {"stage_id", "active"}.intersection(vals.keys()):
            return

        Session = self.env["mega.whatsapp.session"].sudo()

        for lead in self:
            if lead._target_state_is_terminal(vals):
                continue

            closed_session = Session.search(
                [
                    ("lead_id", "=", lead.id),
                    ("active", "=", False),
                    ("step", "=", "done"),
                ],
                order="id desc",
                limit=1,
            )

            if not closed_session:
                continue

            active_session = Session.search(
                [
                    ("phone", "=", closed_session.phone),
                    ("active", "=", True),
                ],
                order="id desc",
                limit=1,
            )

            extra = ""

            if active_session:
                extra = (
                    "\n\nYa existe una sesión WhatsApp activa para este mismo número. "
                    "La nueva conversación debe continuar en la nueva oportunidad."
                )

            raise UserError(
                "No puedes devolver este lead de WhatsApp a una etapa abierta.\n\n"
                "Este lead ya tiene una sesión WhatsApp cerrada. "
                "Si el cliente volvió a escribir, el sistema debe manejarlo como una nueva sesión y un nuevo lead."
                f"{extra}"
            )

    def _close_linked_whatsapp_sessions(self) -> None:
        Session = self.env["mega.whatsapp.session"].sudo()

        for lead in self:
            if not lead._is_whatsapp_terminal_lead():
                continue

            sessions = Session.search(
                [
                    ("lead_id", "=", lead.id),
                    ("active", "=", True),
                ]
            )

            if not sessions:
                continue

            sessions.write(
                {
                    "active": False,
                    "step": "done",
                }
            )

            lead.message_post(
                body=Markup(
                    """
                    <p><strong>Sesión WhatsApp finalizada automáticamente.</strong></p>
                    <p>El lead llegó a un estado final, por lo que la sesión WhatsApp vinculada fue cerrada.</p>
                    """
                ),
                subtype_xmlid="mail.mt_note",
            )

            _logger.info(
                "Closed WhatsApp sessions %s for terminal CRM lead %s",
                sessions.ids,
                lead.id,
            )

    def write(self, vals):
        if self.env.context.get("skip_whatsapp_session_sync"):
            return super().write(vals)

        self._prevent_reopening_closed_whatsapp_leads(vals)

        result = super().write(vals)

        if {"stage_id", "active"}.intersection(vals.keys()):
            self._close_linked_whatsapp_sessions()

        return result
