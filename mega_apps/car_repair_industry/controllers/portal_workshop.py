# -*- coding: utf-8 -*-

from odoo import _, http
from pathlib import Path

from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request


class CarRepairPortalWorkshop(http.Controller):
    RECEPTION_PHOTO_FIELDS = {
        'photo_externa': 'externa',
        'photo_interna': 'interna',
        'photo_dano_existente': 'dano_existente',
        'photo_pertenencias': 'pertenencias',
        'photo_documentos': 'documentos',
        'photo_otro': 'otro',
    }

    def _is_advisor(self):
        return request.env.user.has_group('car_repair_industry.group_fleet_repair_portal_advisor')

    def _is_technician(self):
        return request.env.user.has_group('car_repair_industry.group_fleet_repair_portal_technician')

    def _is_road_test(self):
        return request.env.user.has_group('car_repair_industry.group_fleet_repair_portal_road_test')

    def _is_internal_manager(self):
        return (
            request.env.user.has_group('car_repair_industry.group_fleet_repair_service_manager')
            or request.env.user.has_group('car_repair_industry.group_fleet_repair_directeur_commercial')
            or request.env.user.has_group('base.group_system')
        )

    def _portal_domain(self):
        user = request.env.user
        domains = []
        if self._is_advisor():
            domains.append(('portal_advisor_id', '=', user.id))
        if self._is_technician():
            domains.append(('portal_technician_id', '=', user.id))
        if self._is_road_test():
            domains.append(('road_test_user_id', '=', user.id))
        if self._is_internal_manager():
            return []
        if not domains:
            return [('id', '=', 0)]
        if len(domains) == 1:
            return domains
        domain = ['|'] * (len(domains) - 1)
        for item in domains:
            domain.append(item)
        return domain

    def _get_repair(self, repair_id):
        repair = request.env['fleet.repair'].sudo().browse(repair_id)
        if not repair.exists():
            raise MissingError(_("La orden no existe."))
        allowed = self._is_internal_manager()
        user = request.env.user
        allowed = allowed or (self._is_advisor() and repair.portal_advisor_id.id == user.id)
        allowed = allowed or (self._is_technician() and repair.portal_technician_id.id == user.id)
        allowed = allowed or (self._is_road_test() and repair.road_test_user_id.id == user.id)
        if not allowed:
            raise AccessError(_("No tiene acceso a esta orden."))
        return repair

    def _dashboard_values(self):
        Repair = request.env['fleet.repair'].sudo()
        repairs = Repair.search(self._portal_domain(), order='id desc', limit=80)
        return {
            'repairs': repairs,
            'is_advisor': self._is_advisor(),
            'is_technician': self._is_technician(),
            'is_road_test': self._is_road_test(),
            'is_internal_manager': self._is_internal_manager(),
            'stats': {
                'total': len(repairs),
                'to_assign': len(repairs.filtered(lambda r: r.service_flow_state == 'to_assign')),
                'assigned': len(repairs.filtered(lambda r: r.service_flow_state == 'assigned')),
                'diagnosis': len(repairs.filtered(lambda r: r.service_flow_state == 'diagnosis')),
                'road_test': len(repairs.filtered(lambda r: r.service_flow_state in ('road_test_requested', 'road_test'))),
                'purchase': len(repairs.filtered(lambda r: r.service_flow_state == 'purchase_requested')),
            },
        }

    @http.route(['/my/workshop', '/my/workshop/orders'], type='http', auth='user', website=True)
    def workshop_dashboard(self, **kwargs):
        return request.render('car_repair_industry.portal_workshop_dashboard', self._dashboard_values())

    @http.route('/my/workshop/order/new', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def workshop_order_new(self, **post):
        if not (self._is_advisor() or self._is_internal_manager()):
            return request.render('car_repair_industry.portal_workshop_forbidden', {})

        Template = request.env['fleet.repair.reception.checklist.template'].sudo()
        ServiceType = request.env['service.type'].sudo()
        templates = Template.search([('active', '=', True)], order='name')
        service_types = ServiceType.search([], order='name')
        renting_partner = request.env['fleet.repair'].sudo()._get_renting_partner()
        selected_template = Template.browse(int(post.get('template_id') or 0)) if post.get('template_id') else templates[:1]

        if request.httprequest.method == 'POST':
            validated_files = self._prepare_reception_photo_files()
            repair = self._create_portal_repair(post, selected_template, validated_files)
            return request.redirect('/my/workshop/order/%s' % repair.id)

        return request.render('car_repair_industry.portal_workshop_order_form', {
            'templates': templates,
            'selected_template': selected_template,
            'service_types': service_types,
            'renting_partner': renting_partner,
        })

    def _prepare_reception_photo_files(self):
        Repair = request.env['fleet.repair'].sudo()
        validated_files = []

        uploads = request.httprequest.files.getlist('reception_photos')
        categories = request.httprequest.form.getlist('photo_category')
        for index, upload in enumerate(uploads):
            if not upload or not upload.filename:
                continue
            file_data = Repair._drive_prepare_image_file(
                upload.filename,
                upload.read(),
                mimetype=upload.mimetype,
            )
            category = categories[index] if index < len(categories) else 'otro'
            file_data['evidence_category'] = (
                category if category in self.RECEPTION_PHOTO_FIELDS.values() else 'otro'
            )
            validated_files.append(file_data)

        # Keep accepting the original categorized fields for existing clients.
        for field_name, category in self.RECEPTION_PHOTO_FIELDS.items():
            for upload in request.httprequest.files.getlist(field_name):
                if not upload or not upload.filename:
                    continue
                file_bytes = upload.read()
                file_data = Repair._drive_prepare_image_file(
                    upload.filename,
                    file_bytes,
                    mimetype=upload.mimetype,
                )
                file_data['evidence_category'] = category
                validated_files.append(file_data)
        return validated_files

    def _rename_reception_photo_files(self, repair, files):
        category_sequence = {}
        safe_sequence = (repair.sequence or 'SR').replace('/', '-').replace(' ', '_')
        safe_plate = (repair.license_plate or 'SIN_PLACA').replace('/', '-').replace(' ', '_')
        for file_data in files:
            category = file_data.get('evidence_category') or 'otro'
            category_sequence[category] = category_sequence.get(category, 0) + 1
            extension = Path(file_data['filename']).suffix.lower()
            file_data['filename'] = "%s_%s_recepcion_%s_%03d%s" % (
                safe_sequence,
                safe_plate,
                category,
                category_sequence[category],
                extension,
            )
        return files

    def _create_portal_repair(self, post, template, validated_files):
        Partner = request.env['res.partner'].sudo()
        Repair = request.env['fleet.repair'].sudo()
        ChecklistLine = request.env['fleet.repair.reception.checklist.line'].sudo()

        customer_type = post.get('customer_type') or 'particular'
        client_name = (post.get('client_name') or '').strip()
        client_phone = (post.get('client_phone') or '').strip()
        client_email = (post.get('client_email') or '').strip()
        delivered_by_name = (post.get('delivered_by_name') or '').strip()
        delivered_by_phone = (post.get('delivered_by_phone') or '').strip()

        if customer_type == 'renting':
            partner = Repair._get_renting_partner()
            if not delivered_by_name or not delivered_by_phone:
                raise UserError(_("Para Renting debe registrar nombre y celular de quien entrega el vehículo."))
            client_phone = partner.phone or partner.mobile or ''
            client_email = partner.email or ''
            contact_name = delivered_by_name
            contact_phone = delivered_by_phone
        else:
            if not client_name:
                raise UserError(_("Debe registrar el nombre del cliente particular."))
            partner = Partner.search(['|', ('phone', '=', client_phone), ('mobile', '=', client_phone)], limit=1) if client_phone else Partner.browse()
            if not partner and client_email:
                partner = Partner.search([('email', '=', client_email)], limit=1)
            if not partner:
                partner = Partner.create({
                    'name': client_name,
                    'phone': client_phone,
                    'mobile': client_phone,
                    'email': client_email,
                })
            contact_name = delivered_by_name or client_name
            contact_phone = delivered_by_phone or client_phone

        service_type_id = int(post.get('service_type') or 0)
        values = {
            'name': post.get('reason') or _('Orden de servicio portal'),
            'client_id': partner.id,
            'client_phone': client_phone,
            'client_mobile': client_phone,
            'client_email': client_email,
            'phone': contact_phone,
            'contact_name': contact_name,
            'customer_type': customer_type,
            'renting_reference': post.get('renting_reference'),
            'renting_appointment_validated': bool(post.get('renting_appointment_validated')),
            'delivered_by_name': delivered_by_name or contact_name,
            'delivered_by_phone': delivered_by_phone or contact_phone,
            'delivered_by_document': post.get('delivered_by_document'),
            'delivered_by_email': post.get('delivered_by_email'),
            'delivered_by_observation': post.get('delivered_by_observation'),
            'reception_mileage': float(post.get('reception_mileage') or 0.0),
            'reception_fuel_level': post.get('reception_fuel_level') or False,
            'valuables_inside': post.get('valuables_inside') or False,
            'valuables_description': post.get('valuables_description'),
            'received_documents': post.get('received_documents'),
            'reception_general_observations': post.get('reception_general_observations'),
            'license_plate': (post.get('license_plate') or '').upper(),
            'service_type': service_type_id or False,
            'description': post.get('description'),
            'service_detail': post.get('reason'),
            'portal_advisor_id': request.env.user.id,
            'service_flow_state': 'to_assign',
        }
        repair = Repair.create(values)
        request.env['fleet.repair.line'].sudo().create({
            'fleet_repair_id': repair.id,
            'license_plate': repair.license_plate,
            'service_type': service_type_id or False,
            'service_detail': post.get('reason'),
            'list_of_damage': post.get('description'),
        })

        if template:
            repair.write({'reception_checklist_template_id': template.id})
            for item in template.line_ids.filtered('active'):
                ChecklistLine.create({
                    'repair_id': repair.id,
                    'template_id': template.id,
                    'template_line_id': item.id,
                    'sequence': item.sequence,
                    'name': item.name,
                    'state': post.get('check_state_%s' % item.id) or 'not_apply',
                    'observation': post.get('check_obs_%s' % item.id),
                })

        if validated_files:
            repair._drive_upload_evidence_images(
                self._rename_reception_photo_files(repair, validated_files),
                evidence_type='recepcion',
                description=(
                    post.get('photo_description')
                    or post.get('reception_general_observations')
                    or post.get('description')
                ),
            )

        repair.message_post(body=_("Orden creada desde portal por %s.") % request.env.user.display_name)
        repair.action_flow_mark_to_assign()
        return repair

    @http.route('/my/workshop/order/<int:repair_id>', type='http', auth='user', website=True)
    def workshop_order_detail(self, repair_id, **kwargs):
        try:
            repair = self._get_repair(repair_id)
        except (AccessError, MissingError):
            return request.render('car_repair_industry.portal_workshop_forbidden', {})
        return request.render('car_repair_industry.portal_workshop_order_detail', {
            'repair': repair,
            'is_advisor': self._is_advisor(),
            'is_technician': self._is_technician(),
            'is_road_test': self._is_road_test(),
            'is_internal_manager': self._is_internal_manager(),
        })

    @http.route('/my/workshop/order/<int:repair_id>/technician', type='http', auth='user', website=True, methods=['POST'])
    def workshop_technician_update(self, repair_id, **post):
        repair = self._get_repair(repair_id)
        if not (self._is_technician() or self._is_internal_manager()):
            return request.render('car_repair_industry.portal_workshop_forbidden', {})
        action = post.get('action')
        values = {
            'technical_observation': post.get('technical_observation'),
            'requested_materials': post.get('requested_materials'),
        }
        repair.sudo().write(values)
        if action == 'start':
            repair.sudo().action_flow_start_technician()
        elif action == 'request_road_test':
            repair.sudo().action_flow_request_road_test()
        elif action == 'send_purchase':
            repair.sudo().action_flow_send_to_purchase()
        else:
            repair.message_post(body=_("Avance técnico guardado por %s.") % request.env.user.display_name)
        return request.redirect('/my/workshop/order/%s' % repair.id)

    @http.route('/my/workshop/order/<int:repair_id>/road-test', type='http', auth='user', website=True, methods=['POST'])
    def workshop_road_test_update(self, repair_id, **post):
        repair = self._get_repair(repair_id)
        if not (self._is_road_test() or self._is_internal_manager()):
            return request.render('car_repair_industry.portal_workshop_forbidden', {})
        repair.sudo().write({'road_test_result': post.get('road_test_result')})
        if post.get('action') == 'start':
            repair.sudo().action_flow_start_road_test()
        else:
            repair.sudo().action_flow_finish_road_test()
        return request.redirect('/my/workshop/order/%s' % repair.id)
