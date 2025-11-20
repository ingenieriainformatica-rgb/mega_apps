# -*- coding: utf-8 -*-
import logging
from datetime import date
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

VALIDATE_SEQUENCE = 300  # Límite mínimo de folios antes de alerta
THRESHOLD_DAYS = 30


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    alert_dian = fields.Boolean(
        string="Alert DIAN?",
        default=False,
        tracking=True,
        help="Si está activo, este diario será monitoreado por vencimiento de resolución DIAN o folios restantes."
    )

    # ------------------------------------------------------------
    # MÉTODOS PRIVADOS
    # ------------------------------------------------------------

    def _get_journals_with_dian_alert(self):
        """Retorna los diarios activos con alerta DIAN habilitada."""
        return self.search([('alert_dian', '=', True)])

    def _build_dian_alert_message(self, journal, dias_restantes, fecha_fin):
        """Construye el mensaje HTML para un diario próximo a vencer por fecha."""
        return (
            f"<strong>{journal.display_name}</strong>: "
            f"{dias_restantes} día(s) restantes — "
            f"<strong>vence el {fecha_fin}</strong>."
        )

    def _get_range_number(self, journal):
        """
        Calcula los folios DIAN restantes basados en el último sequence_number.
        Si quedan menos de VALIDATE_SEQUENCE (ej. 300), retorna el mensaje de alerta HTML.
        """
        Move = self.env['account.move']
        last_move = Move.search([
            ('journal_id', '=', journal.id),
            ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
            ('state', '!=', 'cancel'),
            ('sequence_number', '!=', False),
        ], order='sequence_number desc', limit=1)

        last_sequence = last_move.sequence_number or journal.l10n_co_edi_min_range_number or 0
        max_range = journal.l10n_co_edi_max_range_number or 0
        remaining = max_range - last_sequence

        # --- Logging técnico (solo informativo)
        _logger.debug(
            f"[DIAN RANGE] Diario: {journal.name} | Último: {last_sequence} | "
            f"Máximo: {max_range} | Restantes: {remaining}"
        )

        if remaining <= VALIDATE_SEQUENCE:
            return (
                f"<strong>{journal.display_name}</strong>: "
                f"rango DIAN próximo a agotarse "
                f"({remaining} folio(s) restantes de {max_range})."
            )
        return False

    def _collect_active_alerts(self, threshold_days=THRESHOLD_DAYS):
        """
        Recorre los diarios con alerta DIAN activa y genera una lista de mensajes HTML.
        Retorna (alertas_html, diarios_en_riesgo)
        """
        today = date.today()
        alerts, journals_at_risk = [], []

        for journal in self._get_journals_with_dian_alert():
            # --- Validación por rango de folios
            range_alert = self._get_range_number(journal)
            if range_alert:
                alerts.append(range_alert)
                journals_at_risk.append(journal)

            # --- Validación por fecha de resolución
            fecha_fin = journal.l10n_co_edi_dian_authorization_end_date
            if not fecha_fin:
                _logger.warning(f"[DIAN ALERT] Diario '{journal.display_name}' no tiene fecha de finalización configurada.")
                continue

            dias_restantes = (fecha_fin - today).days
            if dias_restantes <= threshold_days:
                alerts.append(self._build_dian_alert_message(journal, dias_restantes, fecha_fin))
                journals_at_risk.append(journal)
                _logger.info(f"[DIAN ALERT] Diario '{journal.display_name}' en riesgo ({dias_restantes} días restantes).")

        return alerts, journals_at_risk

    def _generate_combined_html(self, alerts):
        """Crea el bloque HTML final para mostrar en las facturas."""
        if not alerts:
            return False
        return (
            "<div class='alert alert-danger'>"
            "⚠️ <strong>Resolución DIAN próxima a vencer:</strong><br/>"
            + "<br/>".join(alerts)
            + "</div>"
        )

    # ------------------------------------------------------------
    # MÉTODO PRINCIPAL (CRON)
    # ------------------------------------------------------------

    def cron_check_dian_expiration(self):
        """
        Ejecuta la verificación de resoluciones DIAN próximas a vencer.
        Separa la lógica en pasos claros y reutilizables.
        """
        alerts, journals_at_risk = self._collect_active_alerts()
        alert_html = self._generate_combined_html(alerts)
        moves = self.env['account.move'].search([])

        if alert_html:
            moves_to_update = moves.filtered(lambda m: m.dian_alert_html != alert_html)
            if moves_to_update:
                moves_to_update.write({'dian_alert_html': alert_html})
                _logger.info(
                    f"[DIAN ALERT] {len(moves_to_update)} facturas actualizadas "
                    f"({len(journals_at_risk)} diario(s) con riesgo activo)."
                )
            else:
                _logger.info("[DIAN ALERT] Sin cambios: las alertas ya estaban reflejadas.")
        else:
            moves_with_alerts = moves.filtered(lambda m: m.dian_alert_html)
            if moves_with_alerts:
                moves_with_alerts.write({'dian_alert_html': False})
                _logger.info(f"[DIAN ALERT] Se limpiaron {len(moves_with_alerts)} facturas (sin alertas activas).")
            else:
                _logger.debug("[DIAN ALERT] Sin alertas activas ni facturas para limpiar.")
