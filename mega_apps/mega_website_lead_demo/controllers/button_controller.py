from typing import Any, Optional
from urllib.parse import quote_plus
import logging
import random
import re

from odoo import http, _  #type:ignore
from odoo.http import request  #type:ignore

_logger = logging.getLogger(__name__)


class WebsiteLeadWhatsappController(http.Controller):

    @http.route(
        "/lead/whatsapp/track",
        type="json",
        auth="public",
        website=True,
        csrf=False,
        methods=["POST"],
    )
    def lead_whatsapp_track(self, **post: Any) -> dict[str, Any]:
        # _logger.info("WhatsApp click payload recibido: %s", post)

        try:
            whatsapp_line = self._get_whatsapp_line()

            lead = self._create_whatsapp_click_lead(post, whatsapp_line)
            whatsapp_url = self._build_whatsapp_url(post, lead, whatsapp_line)

            crm_reference = self._get_crm_reference(lead)

            # _logger.info(
            #     "Lead WhatsApp creado correctamente. ID=%s, Referencia=%s, Nombre=%s, Línea WhatsApp=%s",
            #     lead.id,
            #     crm_reference,
            #     lead.name,
            #     whatsapp_line,
            # )

            return {
                "success": True,
                "lead_id": lead.id,
                "lead_name": lead.name,
                "crm_reference": crm_reference,
                "whatsapp_line": whatsapp_line,
                "whatsapp_url": whatsapp_url,
            }

        except Exception as error:
            _logger.exception("Error creando lead desde clic WhatsApp: %s", error)

            whatsapp_line = self._get_whatsapp_line()

            return {
                "success": False,
                "message": str(error),
                "whatsapp_url": self._build_whatsapp_url(
                    post,
                    lead=False,
                    whatsapp_line=whatsapp_line,
                ),
            }

    @http.route(
        "/lead/whatsapp/start",
        type="http",
        auth="public",
        website=True,
        csrf=False,
    )
    def lead_whatsapp_start(self, **post: Any):
        try:
            whatsapp_line = self._get_whatsapp_line()

            lead = self._create_whatsapp_click_lead(post, whatsapp_line)
            whatsapp_url = self._build_whatsapp_url(post, lead, whatsapp_line)

            return request.redirect(whatsapp_url)

        except Exception as error:
            _logger.exception("Error en fallback /lead/whatsapp/start: %s", error)

            whatsapp_line = self._get_whatsapp_line()
            whatsapp_url = self._build_whatsapp_url(
                post,
                lead=False,
                whatsapp_line=whatsapp_line,
            )

            return request.redirect(whatsapp_url)

    def _create_whatsapp_click_lead(
        self,
        post: dict[str, Any],
        whatsapp_line: Optional[dict[str, Any]] = None,
    ):
        Lead = request.env["crm.lead"].sudo()
        website = request.website.sudo()

        website_name = website.name or "Sitio web"

        page_url = self._clean(post.get("page_url"), 1000) or request.httprequest.referrer or ""
        page_path = self._clean(post.get("page_path"), 255) or request.httprequest.path or ""
        page_title = self._clean(post.get("page_title"), 180) or "Página web"
        referrer = self._clean(post.get("referrer"), 1000) or request.httprequest.referrer or ""

        lead_source = self._clean(post.get("lead_source"), 100) or "whatsapp_direct"
        lead_button = self._clean(post.get("lead_button"), 100) or "unknown_button"

        utm_source = self._clean(post.get("utm_source"), 150)
        utm_medium = self._clean(post.get("utm_medium"), 150)
        utm_campaign = self._clean(post.get("utm_campaign"), 150)
        utm_content = self._clean(post.get("utm_content"), 150)
        utm_term = self._clean(post.get("utm_term"), 150)

        ip_address = self._get_client_ip()
        user_agent = self._clean(
            request.httprequest.headers.get("User-Agent", ""),
            500,
        )

        whatsapp_line = whatsapp_line or self._get_whatsapp_line()
        whatsapp_line_name = whatsapp_line.get("name") or ""
        whatsapp_line_phone = whatsapp_line.get("phone") or ""

        description = _(
            "Oportunidad generada por clic directo a WhatsApp.\n\n"
            "Sitio web: %(website_name)s\n"
            "Origen: %(lead_source)s\n"
            "Botón: %(lead_button)s\n\n"
            "Línea WhatsApp asignada: %(whatsapp_line_name)s\n"
            "Número WhatsApp asignado: %(whatsapp_line_phone)s\n\n"
            "Página: %(page_title)s\n"
            "Ruta: %(page_path)s\n"
            "URL: %(page_url)s\n"
            "Referidor: %(referrer)s\n\n"
            "UTM Source: %(utm_source)s\n"
            "UTM Medium: %(utm_medium)s\n"
            "UTM Campaign: %(utm_campaign)s\n"
            "UTM Content: %(utm_content)s\n"
            "UTM Term: %(utm_term)s\n\n"
            "IP: %(ip_address)s\n"
            "User Agent: %(user_agent)s"
        ) % {
            "website_name": website_name,
            "lead_source": lead_source,
            "lead_button": lead_button,
            "whatsapp_line_name": whatsapp_line_name,
            "whatsapp_line_phone": whatsapp_line_phone,
            "page_title": page_title,
            "page_path": page_path,
            "page_url": page_url,
            "referrer": referrer,
            "utm_source": utm_source,
            "utm_medium": utm_medium,
            "utm_campaign": utm_campaign,
            "utm_content": utm_content,
            "utm_term": utm_term,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }

        lead_vals = {
            "name": "WhatsApp directo - creando referencia",
            "type": "opportunity",
            "description": description,
        }

        # Si la línea de WhatsApp tiene asesor/vendedor, se asigna al lead.
        if whatsapp_line.get("user_id") and "user_id" in Lead._fields:
            lead_vals["user_id"] = whatsapp_line["user_id"]

        if "website_id" in Lead._fields:
            lead_vals["website_id"] = website.id

        if "company_id" in Lead._fields and website.company_id:
            lead_vals["company_id"] = website.company_id.id

        if "customer_leaves_battery" in Lead._fields:
            lead_vals["customer_leaves_battery"] = False

        if "page_url" in Lead._fields:
            lead_vals["page_url"] = page_url

        if "website" in Lead._fields:
            lead_vals["website"] = page_url

        self._set_source_if_exists(Lead, lead_vals)
        self._set_tag_if_exists(Lead, lead_vals)

        # _logger.info("Valores para crear lead WhatsApp: %s", lead_vals)

        lead = Lead.create(lead_vals)

        crm_reference = self._get_crm_reference(lead)
        created_at = self._format_created_at(lead)
        created_at_token = self._format_created_at_token(lead)

        final_name = "[%s] WhatsApp directo - %s - %s" % (
            crm_reference,
            website_name,
            created_at_token,
        )

        extra_description = _(
            "\n\n"
            "----------------------------------------\n"
            "Referencia de relación WhatsApp / CRM\n"
            "CRM: %(lead_id)s\n"
            "Referencia: %(crm_reference)s\n"
            "Fecha creación: %(created_at)s\n"
            "Línea WhatsApp: %(whatsapp_line_name)s\n"
            "Número WhatsApp: %(whatsapp_line_phone)s\n"
        ) % {
            "lead_id": lead.id,
            "crm_reference": crm_reference,
            "created_at": created_at,
            "whatsapp_line_name": whatsapp_line_name,
            "whatsapp_line_phone": whatsapp_line_phone,
        }

        update_vals = {
            "name": final_name[:128],
            "description": "%s%s" % (
                lead.description or "",
                extra_description,
            ),
        }

        self._put_if_exists(
            Lead,
            update_vals,
            ("x_whatsapp_crm_id", "x_studio_whatsapp_crm_id", "x_studio_crm_id"),
            str(lead.id),
        )

        self._put_if_exists(
            Lead,
            update_vals,
            ("x_whatsapp_reference", "x_studio_whatsapp_reference", "x_studio_referencia_whatsapp"),
            crm_reference,
        )

        self._put_if_exists(
            Lead,
            update_vals,
            ("x_whatsapp_timestamp", "x_studio_whatsapp_timestamp", "x_studio_fecha_whatsapp"),
            created_at,
        )

        self._put_if_exists(
            Lead,
            update_vals,
            ("x_whatsapp_line_name", "x_studio_whatsapp_line_name", "x_studio_linea_whatsapp"),
            whatsapp_line_name,
        )

        self._put_if_exists(
            Lead,
            update_vals,
            ("x_whatsapp_line_phone", "x_studio_whatsapp_line_phone", "x_studio_numero_whatsapp"),
            whatsapp_line_phone,
        )

        self._put_if_exists(
            Lead,
            update_vals,
            ("x_page_title", "x_studio_page_title"),
            page_title,
        )

        self._put_if_exists(
            Lead,
            update_vals,
            ("x_page_url", "x_studio_page_url"),
            page_url,
        )

        self._put_if_exists(
            Lead,
            update_vals,
            ("x_lead_source", "x_studio_lead_source"),
            lead_source,
        )

        self._put_if_exists(
            Lead,
            update_vals,
            ("x_lead_button", "x_studio_lead_button"),
            lead_button,
        )

        lead.write(update_vals)

        # _logger.info(
        #     "Lead actualizado con referencia WhatsApp. ID=%s, Referencia=%s, Nombre=%s, Línea=%s",
        #     lead.id,
        #     crm_reference,
        #     lead.name,
        #     whatsapp_line,
        # )

        return lead

    def _build_whatsapp_url(
        self,
        post: dict[str, Any],
        lead=False,
        whatsapp_line: Optional[dict[str, Any]] = None,
    ) -> str:
        website = request.website.sudo()

        whatsapp_line = whatsapp_line or self._get_whatsapp_line()
        whatsapp_number = whatsapp_line.get("phone") or "573217718272"

        website_label = self._get_whatsapp_website_label(website)

        if lead:
            message = (
                "Hola %(website_label)s, quiero cotizar mi batería a domicilio. Ref:%(lead_id)s"
            ) % {
                "website_label": website_label,
                "lead_id": lead.id,  # type:ignore
            }
        else:
            message = (
                "Hola %(website_label)s, quiero cotizar mi batería a domicilio."
            ) % {
                "website_label": website_label,
            }

        # _logger.info(
        #     "URL WhatsApp generada. website_id=%s, website_name=%s, whatsapp_line=%s, whatsapp_number=%s",
        #     website.id,
        #     website.name,
        #     whatsapp_line.get("name"),
        #     whatsapp_number,
        # )

        return "https://wa.me/%s?text=%s" % (
            whatsapp_number,
            quote_plus(message),
        )

    def _get_whatsapp_line(self) -> dict[str, Any]:
        website = request.website.sudo()

        fallback_line = {
            "phone": "573217718272",  # 3217718272 - MegaBaterías
            "name": "MegaBaterías",
            "user_id": False,
        }

        if "lead_whatsapp_ids" not in website._fields:
            return fallback_line

        lines = website.lead_whatsapp_ids.sudo().filtered(
            lambda line: line.active and line.phone
        )

        if not lines:
            return fallback_line

        selected = lines[random.randrange(len(lines))]

        return {
            "phone": self._normalize_whatsapp_phone(selected.phone),
            "name": selected.name or "WhatsApp",
            "user_id": selected.user_id.id if "user_id" in selected._fields and selected.user_id else False,
        }

    def _get_whatsapp_number(self) -> str:
        """
        Compatibilidad por si otra parte del módulo todavía llama este método.
        """
        whatsapp_line = self._get_whatsapp_line()
        return whatsapp_line.get("phone") or "573217718272"

    def _set_source_if_exists(self, Lead, lead_vals: dict[str, Any]) -> None:
        if "source_id" not in Lead._fields:
            return

        UtmSource = request.env["utm.source"].sudo()
        source = UtmSource.search([("name", "=", "WhatsApp Web")], limit=1)

        if not source:
            source = UtmSource.create({"name": "WhatsApp Web"})

        lead_vals["source_id"] = source.id

    def _set_tag_if_exists(self, Lead, lead_vals: dict[str, Any]) -> None:
        if "tag_ids" not in Lead._fields:
            return

        CrmTag = request.env["crm.tag"].sudo()
        tag = CrmTag.search([("name", "=", "WhatsApp Web")], limit=1)

        if not tag:
            tag = CrmTag.create({"name": "WhatsApp Web"})

        lead_vals["tag_ids"] = [(4, tag.id)]

    def _get_client_ip(self) -> str:
        forwarded_for = request.httprequest.headers.get("X-Forwarded-For")

        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        return request.httprequest.remote_addr or ""

    @staticmethod
    def _get_crm_reference(lead) -> str:
        return "CRM-%s" % lead.id

    @staticmethod
    def _format_created_at(lead) -> str:
        if not lead or not lead.create_date:
            return ""

        return lead.create_date.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _format_created_at_token(lead) -> str:
        if not lead or not lead.create_date:
            return ""

        return lead.create_date.strftime("%Y%m%d-%H%M%S")

    @staticmethod
    def _put_if_exists(model, vals: dict[str, Any], field_names: tuple[str, ...], value: Any) -> None:
        if value in (None, False, ""):
            return

        for field_name in field_names:
            if field_name in model._fields:
                vals[field_name] = value
                return

    def _get_whatsapp_website_label(self, website) -> str:
        website_labels = {
            2: "Megabaterías",
            19: "Nacional de baterías",
        }

        return website_labels.get(website.id, website.name or "la página web")

    @staticmethod
    def _normalize_whatsapp_phone(phone: str) -> str:
        number = re.sub(r"\D+", "", phone or "")

        # Celular colombiano sin indicativo: 3217718272
        if len(number) == 10 and number.startswith("3"):
            return "57%s" % number

        # Ya viene con indicativo: 573217718272
        if len(number) == 12 and number.startswith("57"):
            return number

        return number

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        return re.sub(r"\D+", "", phone or "")

    @staticmethod
    def _clean(value: Any, max_length: int = 500) -> str:
        return str(value or "").strip()[:max_length]
