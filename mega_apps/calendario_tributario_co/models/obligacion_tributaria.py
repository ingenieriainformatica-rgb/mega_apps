# -*- coding: utf-8 -*-
from odoo import models, fields, api  # type: ignore
from odoo.exceptions import UserError  # type: ignore
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class ObligacionTributaria(models.Model):
    _name = 'obligacion.tributaria'
    _description = 'Obligación Tributaria'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'fecha_limite asc'
    _rec_name = 'display_name'

    # ─── Identificación ────────────────────────────────────────────────────────
    empresa = fields.Selection(
        selection=[
            ('megabaterias',     'Megabaterias'),
            ('megatecnicentro',  'Megatecnicentro'),
            ('impullsar',        'Impullsar'),
        ],
        string='Empresa',
        required=True,
        tracking=True,
    )

    tipo_obligacion = fields.Selection(
        selection=[
            ('renta',               'Renta'),
            ('iva_bimestral',       'IVA Bimestral'),
            ('iva_cuatrimestre',    'IVA Cuatrimestre'),
            ('retencion_fuente',    'Retención en la Fuente'),
            ('exogena',             'Exógena 2026'),
            ('exogena_itagui',      'Exógena Itagui'),
            ('ind_comercio_mde',    'Industria y Comercio Medellín'),
            ('exogena_mde',         'Exógena Medellín'),
            ('exogena_bogota',      'Exógena Bogotá'),
        ],
        string='Tipo de Obligación',
        required=True,
        tracking=True,
    )

    fecha_limite = fields.Date(
        string='Fecha Límite',
        required=True,
        tracking=True,
    )

    estado = fields.Selection(
        selection=[
            ('pendiente',   'Pendiente'),
            ('en_proceso',  'En proceso'),
            ('pagado',      'Pagado / Presentado'),
            ('no_aplica',   'No aplica'),
        ],
        string='Estado',
        default='pendiente',
        tracking=True,
    )

    aplica = fields.Boolean(
        string='Aplica',
        default=True,
        help='Desmarcar si esta obligación no aplica para esta empresa.',
    )

    # ─── Información adicional ─────────────────────────────────────────────────
    monto = fields.Monetary(
        string='Monto Estimado',
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id,
    )
    fecha_pago = fields.Date(string='Fecha de Pago Real', tracking=True)
    numero_formulario = fields.Char(string='Número de Formulario / Radicado')
    notas = fields.Text(string='Notas')

    # ─── Campos computados ────────────────────────────────────────────────────
    dias_restantes = fields.Integer(
        string='Días Restantes',
        compute='_compute_dias_restantes',
        store=False,
    )

    prioridad = fields.Selection(
        selection=[
            ('0', 'Normal'),
            ('1', 'Urgente'),
            ('2', 'Crítico'),
        ],
        string='Prioridad',
        compute='_compute_prioridad',
        store=False,
    )

    alerta_enviada_5d = fields.Boolean(string='Alerta 5 días enviada', default=False)
    alerta_enviada_3d = fields.Boolean(string='Alerta 3 días enviada', default=False)
    alerta_enviada_1d = fields.Boolean(string='Alerta 1 día enviada',  default=False)

    display_name = fields.Char(compute='_compute_display_name', store=True)

    # ─── Responsables ─────────────────────────────────────────────────────────
    responsable_ids = fields.Many2many(
        'res.users',
        string='Administradores / Responsables',
        domain="[('share', '=', False)]",
        help='Usuarios que recibirán las notificaciones de esta obligación.',
    )

    # ─── Computes ─────────────────────────────────────────────────────────────
    @api.depends('empresa', 'tipo_obligacion', 'fecha_limite')
    def _compute_display_name(self):
        empresa_map = {
            'megabaterias':    'Megabaterias',
            'megatecnicentro': 'Metatecnicentro',
            'impullsar':       'Impullsar',
        }
        tipo_map = {
            'renta':            'Renta',
            'iva_bimestral':    'IVA Bimestral',
            'iva_cuatrimestre': 'IVA Cuatrimestre',
            'retencion_fuente': 'Retención',
            'exogena':          'Exógena',
            'exogena_itagui':   'Exógena Itagui',
            'ind_comercio_mde': 'Ind. y Comercio MDE',
            'exogena_mde':      'Exógena MDE',
            'exogena_bogota':   'Exógena Bogotá',
        }
        for rec in self:
            emp  = empresa_map.get(rec.empresa, rec.empresa or '')
            tipo = tipo_map.get(rec.tipo_obligacion, rec.tipo_obligacion or '')
            fecha = rec.fecha_limite.strftime('%d/%m/%Y') if rec.fecha_limite else ''
            rec.display_name = f"[{emp}] {tipo} – {fecha}"

    @api.depends('fecha_limite', 'estado')
    def _compute_dias_restantes(self):
        hoy = date.today()
        for rec in self:
            if rec.fecha_limite and rec.estado not in ('pagado', 'no_aplica'):
                rec.dias_restantes = (rec.fecha_limite - hoy).days
            else:
                rec.dias_restantes = 0

    @api.depends('dias_restantes', 'estado')
    def _compute_prioridad(self):
        for rec in self:
            d = rec.dias_restantes
            if rec.estado in ('pagado', 'no_aplica'):
                rec.prioridad = '0'
            elif d <= 1:
                rec.prioridad = '2'
            elif d <= 3:
                rec.prioridad = '1'
            else:
                rec.prioridad = '0'

    # ─── Lógica de notificaciones ──────────────────────────────────────────────
    def _get_destinatarios(self):
        """Retorna lista de usuarios a notificar: responsables del registro
        o, si no hay, todos los usuarios del grupo contabilidad."""
        self.ensure_one()
        if self.responsable_ids:
            return self.responsable_ids
        grupo = self.env.ref('account.group_account_manager', raise_if_not_found=False)
        if grupo:
            return grupo.users
        return self.env['res.users'].search([('share', '=', False)])

    def _enviar_alerta(self, dias):
        """Envía notificación interna (chatter) y correo a los responsables."""
        self.ensure_one()
        hoy = date.today()
        empresa_label = dict(self._fields['empresa'].selection).get(self.empresa, self.empresa)
        tipo_label    = dict(self._fields['tipo_obligacion'].selection).get(
                            self.tipo_obligacion, self.tipo_obligacion)

        if dias > 0:
            asunto = f"⚠️ ALERTA TRIBUTARIA – {empresa_label} | {tipo_label} vence en {dias} día(s)"
            emoji  = "🔴" if dias == 1 else ("🟠" if dias <= 3 else "🟡")
        else:
            asunto = f"🚨 VENCIDA – {empresa_label} | {tipo_label} venció hace {abs(dias)} día(s)"
            emoji  = "🚨"

        cuerpo_html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;">
          <div style="background:#1a1a2e;color:#fff;padding:16px 24px;">
            <h2 style="margin:0;font-size:18px;">{emoji} Alerta de Obligación Tributaria</h2>
          </div>
          <div style="padding:24px;">
            <table style="width:100%;border-collapse:collapse;font-size:14px;">
              <tr><td style="padding:8px 0;color:#555;width:180px;"><b>Empresa</b></td>
                  <td style="padding:8px 0;">{empresa_label}</td></tr>
              <tr style="background:#f9f9f9;">
                  <td style="padding:8px 0;color:#555;"><b>Obligación</b></td>
                  <td style="padding:8px 0;">{tipo_label}</td></tr>
              <tr><td style="padding:8px 0;color:#555;"><b>Fecha límite</b></td>
                  <td style="padding:8px 0;">{self.fecha_limite.strftime('%d de %B de %Y')}</td></tr>
              <tr style="background:#f9f9f9;">
                  <td style="padding:8px 0;color:#555;"><b>Días restantes</b></td>
                  <td style="padding:8px 0;font-weight:bold;color:{'#c0392b' if dias <= 1 else '#e67e22' if dias <= 3 else '#f39c12'};">
                    {dias} día(s)</td></tr>
              <tr><td style="padding:8px 0;color:#555;"><b>Estado</b></td>
                  <td style="padding:8px 0;">{dict(self._fields['estado'].selection).get(self.estado,'')}</td></tr>
              {'<tr style="background:#f9f9f9;"><td style="padding:8px 0;color:#555;"><b>Monto estimado</b></td><td style="padding:8px 0;">$ {:,.0f}</td></tr>'.format(self.monto) if self.monto else ''}
            </table>
            <div style="margin-top:20px;padding:12px;background:#fff3cd;border-left:4px solid #ffc107;border-radius:4px;">
              <p style="margin:0;font-size:13px;">
                Por favor gestione esta obligación a la brevedad para evitar sanciones e intereses moratorios.
              </p>
            </div>
          </div>
          <div style="padding:12px 24px;background:#f5f5f5;font-size:12px;color:#888;">
            Generado automáticamente el {hoy.strftime('%d/%m/%Y')} · Sistema Calendario Tributario 2026
          </div>
        </div>
        """

        # Notificación interna (chatter)
        destinatarios = self._get_destinatarios()
        partner_ids   = destinatarios.mapped('partner_id').ids

        self.message_post(
            body=cuerpo_html,
            subject=asunto,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            partner_ids=partner_ids,
        )

        # Correo externo
        template_vals = {
            'subject':      asunto,
            'body_html':    cuerpo_html,
            'email_from':   self.env.company.email or 'noreply@example.com',
            'email_to':     ','.join(destinatarios.mapped('email') or []),
        }
        if template_vals['email_to']:
            mail = self.env['mail.mail'].create(template_vals)
            mail.send()
            _logger.info("Alerta tributaria enviada: %s → %s", asunto, template_vals['email_to'])

    # ─── Cron: revisión diaria ─────────────────────────────────────────────────
    @api.model
    def cron_verificar_alertas(self):
        """Ejecutado cada día a las 08:00 AM.
        Envía alertas escalonadas: 5 días → 3 días → 1 día antes."""
        pendientes = self.search([
            ('estado', 'not in', ['pagado', 'no_aplica']),
            ('aplica', '=', True),
            ('fecha_limite', '>=', date.today()),
        ])

        for ob in pendientes:
            dias = (ob.fecha_limite - date.today()).days

            if dias == 5 and not ob.alerta_enviada_5d:
                ob._enviar_alerta(5)
                ob.alerta_enviada_5d = True

            elif dias == 3 and not ob.alerta_enviada_3d:
                ob._enviar_alerta(3)
                ob.alerta_enviada_3d = True

            elif dias == 1 and not ob.alerta_enviada_1d:
                ob._enviar_alerta(1)
                ob.alerta_enviada_1d = True

        # Verificar vencidas (sin pagar)
        vencidas = self.search([
            ('estado', 'not in', ['pagado', 'no_aplica']),
            ('aplica', '=', True),
            ('fecha_limite', '<', date.today()),
        ])
        for ob in vencidas:
            dias = (ob.fecha_limite - date.today()).days
            ob._enviar_alerta(dias)
            _logger.warning("Obligación VENCIDA detectada: %s", ob.display_name)

    # ─── Acción manual de prueba ───────────────────────────────────────────────
    def action_enviar_alerta_manual(self):
        """Botón para probar el envío de alerta manualmente."""
        self.ensure_one()
        self._enviar_alerta(self.dias_restantes)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Alerta enviada',
                'message': f'Notificación enviada correctamente para {self.display_name}',
                'type': 'success',
                'sticky': False,
            },
        }

    def action_marcar_pagado(self):
        self.ensure_one()
        self.write({
            'estado': 'pagado',
            'fecha_pago': date.today(),
        })


# ─── Tabla de historial de alertas enviadas ──────────────────────────────────
class HistorialAlertaTributaria(models.Model):
    _name = 'historial.alerta.tributaria'
    _description = 'Historial de Alertas Tributarias'
    _order = 'fecha_envio desc'

    obligacion_id = fields.Many2one(
        'obligacion.tributaria',
        string='Obligación',
        ondelete='cascade',
        required=True,
    )
    fecha_envio   = fields.Datetime(string='Fecha de Envío', default=fields.Datetime.now)
    dias_antes    = fields.Integer(string='Días antes del vencimiento')
    canal         = fields.Selection(
        [('email', 'Correo'), ('interno', 'Notificación interna'), ('ambos', 'Ambos')],
        string='Canal',
        default='ambos',
    )
    destinatarios = fields.Char(string='Destinatarios')
    resultado     = fields.Selection(
        [('enviado', 'Enviado'), ('error', 'Error')],
        string='Resultado',
        default='enviado',
    )
