from odoo import http  # type: ignore
from odoo.http import request  # type: ignore
from urllib.parse import quote
from werkzeug.utils import redirect  # type: ignore


class WebsiteLeadDemoController(http.Controller):

    @http.route('/lead_demo/test', type='http', auth='public', website=True, csrf=False)
    def lead_demo_test(self, **post):
        invoice_name = (post.get('invoice_name') or '').strip()
        vat = (post.get('vat') or '').strip()
        phone = (post.get('phone') or '').strip()
        street = (post.get('street') or '').strip()
        email = (post.get('email') or '').strip()
        brand_brand = (post.get('brand_brand') or '').strip()
        brand_model = (post.get('brand_model') or '').strip()
        license_plate = (post.get('license_plate') or '').strip()
        website_name = post.get('website_name') or ''
        accept_terms = post.get('accept_terms')

        client_ip = request.httprequest.headers.get('X-Forwarded-For')
        if client_ip:
            client_ip = client_ip.split(',')[0].strip()
        else:
            client_ip = request.httprequest.remote_addr

        base_url = request.httprequest.host_url.rstrip('/')

        if not invoice_name or not vat or not phone or not email or not license_plate:
            return request.redirect('/')

        if not accept_terms:
            return request.redirect('/')

        description = (
            f"Lead creado desde modal website.\n<br />"
            f"Website: {website_name}\n<br />"
            f"Dominio: {base_url}\n<br />"
            f"IP Cliente: {client_ip}\n<br />"
            f"Aceptó términos: Sí\n\n<br />"
            f"Nombre de quien sale la factura: {invoice_name}\n<br />"
            f"Cédula o NIT: {vat}\n<br />"
            f"Teléfono: {phone}\n<br />"
            f"Dirección: {street}\n<br />"
            f"Correo electrónico: {email}\n<br />"
            f"Marca: {brand_brand}\n<br />"
            f"Modelo: {brand_model}\n<br />"
            f"Placa: {license_plate}\n"
        )

        lead = request.env['crm.lead'].sudo().create({
            'name': f'Lead web - {invoice_name}',
            'contact_name': invoice_name,
            'phone': phone,
            'email_from': email,
            'street': street,
            'description': description,
        })

        whatsapp_number = "573193662738"
        whatsapp_message = (
            "Nuevo lead desde la web\n\n"
            f"Lead: {lead.name}\n"
            f"Nombre: {invoice_name}\n"
            f"Cédula/NIT: {vat}\n"
            f"Teléfono: {phone}\n"
            f"Dirección: {street}\n"
            f"Correo: {email}\n"
            f"Placa: {license_plate}\n"
            f"Marca: {brand_brand}\n"
            f"Modelo: {brand_model}\n"
            f"Website: {website_name}\n"
            f"Dominio: {base_url}\n"
        )

        whatsapp_url = f"https://wa.me/{whatsapp_number}?text={quote(whatsapp_message)}"
        return redirect(whatsapp_url)
