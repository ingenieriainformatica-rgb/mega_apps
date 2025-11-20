# models/mega_billing_alert.py
import logging
from collections import defaultdict
from odoo import models, api, fields  #type: ignore
from odoo.tools.misc import format_amount  #type: ignore

_logger = logging.getLogger(__name__)
TO_INVOICE = 'to invoice'

class MegaBillingAlert(models.TransientModel):
    _name = "mega.billing.alert"
    _description = "Mega - Alertas de facturación"

    html_table = fields.Html(string="Tabla HTML", sanitize=False)

    def _build_html_table(self, orders):
        icp = self.env['ir.config_parameter'].sudo()
        base_url = (icp.get_param('web.base.url') or '').rstrip('/')
        rows = []
        for so in orders:
            link = f"{base_url}/web#id={so.id}&model=sale.order&view_type=form"
            amt = format_amount(self.env, so.amount_total or 0.0, so.currency_id or self.env.company.currency_id)
            rows.append(
                "<tr>"
                f"<td style='text-align:center'><a href=\"{link}\">{so.id}</a></td>"
                f"<td>{so.date_order}</td>"
                f"<td>{so.partner_id.name}</td>"
                f"<td>{so.user_id.name}</td>"
                f"<td><a href=\"{link}\">{so.name}</a></td>"
                f"<td style='text-align:right'>{amt}</td>"
                "</tr>"
            )
        return (
            "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;width:100%'>"
            "<thead style='background:#f3f4f6'><tr>"
            "<th style='width:80px;text-align:center'>ID</th>"
            "<th>Fecha de la orden</th>"
            "<th>Cliente</th>"
            "<th>Vendedor</th>"
            "<th>Orden</th>"
            "<th style='width:160px;text-align:right'>Total</th>"
            "</tr></thead><tbody>"
            + "\n".join(rows) +
            "</tbody></table>"
        )

    # --- NUEVO: destinatarios desde grupo (o parámetro, o fallback usuario actual) ---
    def _resolve_recipients(self, company):
        icp = self.env['ir.config_parameter'].sudo()
        # 1) Si hay parámetro, se respeta (coma-separados)
        param = (icp.get_param('mega.billing.alert.recipients', '') or '').strip()
        if param:
            return param

        # 2) Si no hay parámetro, tomamos usuarios del grupo
        emails = []
        try:
            group = self.env.ref('mega_send_billing_by_email.group_billing_alert_recipients')
            users = group.users.filtered(lambda u: u.active and u.partner_id.email and (company in u.company_ids))
            emails = [u.partner_id.email for u in users]
        except Exception as e:
            _logger.warning("No se encontró el grupo de destinatarios: %s", e)

        emails = list(dict.fromkeys(emails))  # únicos
        if emails:
            return ",".join(emails)

        # 3) Fallback: correo del usuario actual
        return self.env.user.partner_id.email or ''

    # Opcional: escoger servidor SMTP por parámetro para evitar 'fallback'
    def _resolve_mail_server_id(self):
        icp = self.env['ir.config_parameter'].sudo()
        val = icp.get_param('mega.billing.alert.smtp_server_id')
        try:
            return int(val) if val else False
        except Exception:
            return False

    def action_send_template(self, recipients=None):
        template = self.env.ref('mega_send_billing_by_email.mail_template_mega_send_billing', raise_if_not_found=False)
        if not template:
            _logger.warning("Template 'mail_template_mega_send_billing' no existe.")
            return False
        for rec in self:
            email_values = {}
            if recipients:
                email_values['email_to'] = recipients
            smtp_id = self._resolve_mail_server_id()
            if smtp_id:
                email_values['mail_server_id'] = smtp_id
            template.sudo().send_mail(rec.id, force_send=True, email_values=email_values)
        return True

    @api.model
    def send_billing_alerts_cron(self):
        Sale = self.env['sale.order']
        domain = [('invoice_status', '=', TO_INVOICE)]  # ← tal cual lo pediste
        orders = Sale.search(domain, order='date_order desc')
        if not orders:
            _logger.info("MegaBillingAlert: no hay órdenes por facturar.")
            return True

        by_company = defaultdict(lambda: self.env['sale.order'])
        for so in orders:
            by_company[so.company_id] |= so

        icp = self.env['ir.config_parameter'].sudo()
        try:
            max_rows = int(icp.get_param('mega.billing.alert.max_rows', '200'))
        except Exception:
            max_rows = 200

        sent = 0
        for company, c_orders in by_company.items():
            to_send = c_orders[:max_rows]
            html_table = self._build_html_table(to_send)
            wiz = self.create({'html_table': html_table})

            recipients = self._resolve_recipients(company)
            if recipients:
                wiz.action_send_template(recipients=recipients)
                sent += 1
                _logger.info("MegaBillingAlert: enviado a %s (SO=%d) para compañía %s",
                             recipients, len(to_send), company.name)
            else:
                _logger.warning("MegaBillingAlert: sin destinatarios (configura grupo o parámetro).")

        return bool(sent)
