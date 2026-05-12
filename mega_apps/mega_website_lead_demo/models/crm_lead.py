import logging
from datetime import timedelta

from odoo import models, fields, api, _  # type:ignore
from odoo.exceptions import UserError  # type:ignore

_logger = logging.getLogger(__name__)


class CRMLead(models.Model):
    _inherit = "crm.lead"

    crm_fecha_instalacion = fields.Datetime(
        string="Fecha de Instalación",
        tracking=True,
    )

    crm_tiempo_transcurrido = fields.Char(
        string="Tiempo Transcurrido",
        compute="_compute_tiempo_transcurrido",
        store=True,
    )

    crm_kanban_alert = fields.Selection(
        selection=[
            ("normal", "Normal"),
            ("warning", "Advertencia"),
            ("danger", "Crítico"),
        ],
        string="Alerta Kanban",
        compute="_compute_crm_kanban_alert",
        store=True,
    )

    @api.depends("crm_fecha_instalacion", "stage_id")
    def _compute_tiempo_transcurrido(self):
        for lead in self:
            if not lead.crm_fecha_instalacion:
                lead.crm_tiempo_transcurrido = ""
                continue

            # Si es etapa final, congelar
            if lead.stage_id.is_won or lead.stage_id.fold:
                if not lead.crm_tiempo_transcurrido:
                    now = fields.Datetime.now()
                    diff = now - lead.crm_fecha_instalacion
                    lead.crm_tiempo_transcurrido = lead._formatear_tiempo(diff)
                continue

            now = fields.Datetime.now()
            diff = now - lead.crm_fecha_instalacion
            lead.crm_tiempo_transcurrido = lead._formatear_tiempo(diff)

    @api.depends("crm_fecha_instalacion", "stage_id")
    def _compute_crm_kanban_alert(self):
        now = fields.Datetime.now()

        for lead in self:
            lead.crm_kanban_alert = "normal"

            if not lead.crm_fecha_instalacion:
                continue

            # Si ya está ganado o cerrado, no pintar alerta
            if lead.stage_id.is_won or lead.stage_id.fold:
                lead.crm_kanban_alert = "normal"
                continue

            diff = now - lead.crm_fecha_instalacion

            if diff >= timedelta(hours=1):
                lead.crm_kanban_alert = "danger"
            elif diff >= timedelta(minutes=30):
                lead.crm_kanban_alert = "warning"

    def _formatear_tiempo(self, diff):
        days = diff.days
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def _cron_actualizar_tiempos(self):
        """CRON: Recalcula tiempos y alertas solo en leads que NO están en etapa final."""
        leads = self.search([
            ("crm_fecha_instalacion", "!=", False),
            ("stage_id.is_won", "=", False),
            ("stage_id.fold", "=", False),
        ])

        if leads:
            leads._compute_tiempo_transcurrido()
            leads._compute_crm_kanban_alert()
            _logger.info("CRON: %s leads actualizados", len(leads))

    def unlink(self):
        if not self.env.user.has_group("mega_website_lead_demo.group_delete_leads_crm"):
            grupo = self.env.ref(
                "mega_website_lead_demo.group_delete_leads_crm",
                raise_if_not_found=False,
            )
            nombre_grupo = grupo.name if grupo else "Allow deletion of Leads CRM"

            raise UserError(_(
                'No tienes permiso para eliminar leads.\n'
                'Grupo: "%s".\n'
                'Contacta al administrador del sistema.'
            ) % nombre_grupo)

        return super().unlink()
