# -*- coding: utf-8 -*-

import json
from odoo import _, fields, http
from pathlib import Path

from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager

_WORKSHOP_REPAIRS_PER_PAGE = 20


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

    FILTER_STATE_MAP = {
        'to_assign': ('==', 'to_assign'),
        'assigned': ('==', 'assigned'),
        'diagnosis': ('==', 'diagnosis'),
        'road_test': ('in', ('road_test_requested', 'road_test')),
        'purchase': ('==', 'purchase_requested'),
    }

    def _dashboard_values(self, active_filter='all', search='', page=1):
        Repair = request.env['fleet.repair'].sudo()
        base_domain = self._portal_domain()

        # Filter domain applied on top of base access domain
        filter_domain = list(base_domain)
        if active_filter in self.FILTER_STATE_MAP:
            op, val = self.FILTER_STATE_MAP[active_filter]
            if op == '==':
                filter_domain.append(('service_flow_state', '=', val))
            else:
                filter_domain.append(('service_flow_state', 'in', list(val)))

        # Search domain applied on top of filter domain
        search_domain = list(filter_domain)
        if search:
            search_domain += ['|', '|', '|',
                ('sequence', 'ilike', search),
                ('license_plate', 'ilike', search),
                ('client_id.name', 'ilike', search),
                ('name', 'ilike', search),
            ]

        repair_count = Repair.search_count(search_domain)

        url_args = {}
        if active_filter != 'all':
            url_args['filter'] = active_filter
        if search:
            url_args['search'] = search

        pager_values = portal_pager(
            url='/my/workshop',
            total=repair_count,
            page=page,
            step=_WORKSHOP_REPAIRS_PER_PAGE,
            scope=7,
            url_args=url_args,
        )

        repairs = Repair.search(
            search_domain,
            order='id desc',
            limit=_WORKSHOP_REPAIRS_PER_PAGE,
            offset=pager_values['offset'],
        )

        # Stats always reflect all accessible repairs (no search/filter applied)
        stats = {
            'total': Repair.search_count(base_domain),
            'to_assign': Repair.search_count(base_domain + [('service_flow_state', '=', 'to_assign')]),
            'assigned': Repair.search_count(base_domain + [('service_flow_state', '=', 'assigned')]),
            'diagnosis': Repair.search_count(base_domain + [('service_flow_state', '=', 'diagnosis')]),
            'road_test': Repair.search_count(base_domain + [('service_flow_state', 'in', ['road_test_requested', 'road_test'])]),
            'purchase': Repair.search_count(base_domain + [('service_flow_state', '=', 'purchase_requested')]),
        }

        return {
            'repairs': repairs,
            'repair_count': repair_count,
            'search': search,
            'pager': pager_values,
            'is_advisor': self._is_advisor(),
            'is_technician': self._is_technician(),
            'is_road_test': self._is_road_test(),
            'is_internal_manager': self._is_internal_manager(),
            'active_filter': active_filter,
            'stats': stats,
        }

    @http.route(
        ['/my/workshop', '/my/workshop/orders', '/my/workshop/page/<int:page>'],
        type='http', auth='user', website=True,
    )
    def workshop_dashboard(self, filter=None, search='', page=1, **kwargs):
        active_filter = filter if filter in self.FILTER_STATE_MAP else 'all'
        search = (search or '').strip()
        try:
            page = max(1, int(page))
        except (TypeError, ValueError):
            page = 1
        return request.render(
            'car_repair_industry.portal_workshop_dashboard',
            self._dashboard_values(active_filter, search, page),
        )

    @http.route('/my/workshop/order/new', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def workshop_order_new(self, **post):
        if not (self._is_advisor() or self._is_internal_manager()):
            return request.render('car_repair_industry.portal_workshop_forbidden', {})

        Template = request.env['fleet.repair.reception.checklist.template'].sudo()
        ServiceType = request.env['service.type'].sudo()
        VehicleModel = request.env['fleet.vehicle.model'].sudo()
        VehicleBrand = request.env['fleet.vehicle.model.brand'].sudo()
        templates = Template.search([('active', '=', True)], order='name')
        service_types = ServiceType.search([], order='name')
        vehicle_models = VehicleModel.search([], order='name')
        vehicle_brands = VehicleBrand.search([], order='name')
        renting_partner = request.env['fleet.repair'].sudo()._find_renting_partner()
        selected_template = Template.browse(int(post.get('template_id') or 0)) if post.get('template_id') else templates[:1]

        if request.httprequest.method == 'POST':
            validated_files = self._prepare_reception_photo_files()
            repair = self._create_portal_repair(post, selected_template, validated_files)
            return request.redirect('/my/workshop/order/%s' % repair.id)

        return request.render('car_repair_industry.portal_workshop_order_form', {
            'templates': templates,
            'selected_template': selected_template,
            'service_types': service_types,
            'vehicle_models': vehicle_models,
            'vehicle_brands': vehicle_brands,
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
        elif customer_type == 'corporate':
            company_name = (post.get('company_name') or '').strip()
            company_vat = (post.get('company_vat') or '').strip()
            if not company_name:
                raise UserError(_("Para Corporativo debe registrar la razón social de la empresa."))
            if not delivered_by_name or not delivered_by_phone:
                raise UserError(_("Para Corporativo debe registrar nombre y celular de quien entrega el vehículo."))
            partner = Partner.browse()
            if company_vat:
                partner = Partner.search([('vat', '=', company_vat)], limit=1)
            if not partner:
                partner = Partner.search([('name', '=ilike', company_name), ('is_company', '=', True)], limit=1)
            if not partner:
                partner = Partner.create({
                    'name': company_name,
                    'is_company': True,
                    'vat': company_vat,
                    'phone': delivered_by_phone,
                    'mobile': delivered_by_phone,
                    'email': delivered_by_email or client_email,
                })
            client_phone = partner.phone or partner.mobile or delivered_by_phone
            client_email = partner.email or client_email
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

        service_type_ids = []
        raw_service_types = request.httprequest.form.getlist('service_types')
        for raw in raw_service_types:
            try:
                service_type_ids.append(int(raw))
            except (TypeError, ValueError):
                continue
        if not service_type_ids:
            raise UserError(_("Debe seleccionar al menos un servicio."))
        primary_service_type_id = service_type_ids[0]
        vehicle_brand_id = int(post.get('vehicle_brand_id') or 0)
        vehicle_model_id = int(post.get('vehicle_model_id') or 0)
        model_year = (post.get('model_year') or '').strip()
        engine_displacement = (post.get('engine_displacement') or '').strip()
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
            'model_id': vehicle_model_id or False,
            'vehicle_brand_id': vehicle_brand_id or False,
            'model_year': model_year or False,
            'engine_displacement': engine_displacement or False,
            'engine_number': (post.get('engine_number') or '').strip() or False,
            'vin_sn': (post.get('vin_sn') or '').strip().upper() or False,
            'fuel_type': post.get('fuel_type') or False,
            'service_type': primary_service_type_id or False,
            'description': post.get('description'),
            'service_detail': post.get('reason'),
            'portal_advisor_id': request.env.user.id,
            'service_flow_state': 'to_assign',
        }
        repair = Repair.create(values)
        RepairLine = request.env['fleet.repair.line'].sudo()
        for index, service_id in enumerate(service_type_ids, start=1):
            RepairLine.create({
                'fleet_repair_id': repair.id,
                'license_plate': repair.license_plate,
                'model_id': vehicle_model_id or False,
                'vehicle_brand_id': vehicle_brand_id or False,
                'model_year': model_year or False,
                'engine_displacement': engine_displacement or False,
                'engine_number': repair.engine_number or False,
                'vin_sn': repair.vin_sn or False,
                'fuel_type': post.get('fuel_type') or False,
                'service_type': service_id or False,
                'service_detail': post.get('reason') if index == 1 else False,
                'list_of_damage': post.get('description') if index == 1 else False,
                'tecnico_status': 'pendiente',
            })

        if template:
            repair.write({'reception_checklist_template_id': template.id})
            for item in template.line_ids.filtered('active'):
                ChecklistLine.create({
                    'repair_id': repair.id,
                    'checklist_type': 'asesor',
                    'template_id': template.id,
                    'template_line_id': item.id,
                    'sequence': item.sequence,
                    'name': item.name,
                    'state': post.get('check_state_%s' % item.id) or 'not_apply',
                    'observation': post.get('check_obs_%s' % item.id),
                })

        self._ensure_tecnico_checklist_lines(repair)

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
        self._ensure_tecnico_checklist_lines(repair)
        return request.render('car_repair_industry.portal_workshop_order_detail', {
            'repair': repair,
            'service_lines': request.env['fleet.repair.line'].sudo().search(
                [('fleet_repair_id', '=', repair.id)], order='id asc'
            ),
            'is_advisor': self._is_advisor(),
            'is_technician': self._is_technician(),
            'is_road_test': self._is_road_test(),
            'is_internal_manager': self._is_internal_manager(),
        })

    def _ensure_tecnico_checklist_lines(self, repair):
        ChecklistLine = request.env['fleet.repair.reception.checklist.line'].sudo()
        existing_tecnico = ChecklistLine.search_count([
            ('repair_id', '=', repair.id),
            ('checklist_type', '=', 'tecnico'),
        ])
        if existing_tecnico:
            return
        tecnico_template = request.env['fleet.repair.reception.checklist.template'].sudo().search([
            ('name', '=ilike', 'Checklist técnico'),
            ('active', '=', True),
        ], limit=1)
        if not tecnico_template:
            return
        for item in tecnico_template.line_ids.filtered('active'):
            ChecklistLine.create({
                'repair_id': repair.id,
                'checklist_type': 'tecnico',
                'template_id': tecnico_template.id,
                'template_line_id': item.id,
                'sequence': item.sequence,
                'name': item.name,
                'state': 'not_apply',
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

        RepairLine = request.env['fleet.repair.line'].sudo()
        service_lines = RepairLine.search([('fleet_repair_id', '=', repair.id)])
        allowed_statuses = {'pendiente', 'en_progreso', 'completado'}
        for line in service_lines:
            new_status = post.get('svc_status_%s' % line.id)
            new_notes = post.get('svc_notes_%s' % line.id)
            write_vals = {}
            if new_status in allowed_statuses:
                write_vals['tecnico_status'] = new_status
            if new_notes is not None:
                write_vals['tecnico_notes'] = new_notes
            if write_vals:
                line.write(write_vals)

        ChecklistLine = request.env['fleet.repair.reception.checklist.line'].sudo()
        tecnico_lines = ChecklistLine.search([
            ('repair_id', '=', repair.id),
            ('checklist_type', '=', 'tecnico'),
        ])
        allowed_states = {'good', 'regular', 'bad', 'not_apply'}
        allowed_repaired = {'yes', 'no', 'pending'}
        for line in tecnico_lines:
            state = post.get('tech_state_%s' % line.id)
            observation = post.get('tech_obs_%s' % line.id)
            repaired = post.get('tech_repaired_%s' % line.id)
            measurement_left = post.get('tech_measure_left_%s' % line.id)
            measurement_right = post.get('tech_measure_right_%s' % line.id)
            position = post.get('tech_position_%s' % line.id)
            expiration_date = post.get('tech_expiration_%s' % line.id)
            write_vals = {}
            if state in allowed_states:
                write_vals['state'] = state
            if observation is not None:
                write_vals['observation'] = observation
            if repaired in allowed_repaired:
                write_vals['repaired'] = repaired
            if measurement_left is not None:
                write_vals['measurement_left'] = measurement_left
            if measurement_right is not None:
                write_vals['measurement_right'] = measurement_right
            if position is not None:
                write_vals['position'] = position
            if expiration_date:
                try:
                    from datetime import datetime
                    write_vals['expiration_date'] = datetime.strptime(expiration_date, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass
            if write_vals:
                line.write(write_vals)

        if action == 'start':
            repair.sudo().action_flow_start_technician()
        elif action == 'request_road_test':
            repair.sudo().action_flow_request_road_test()
        elif action == 'send_purchase':
            repair.sudo().action_flow_send_to_purchase()
        else:
            repair.message_post(body=_("Avance técnico guardado por %s.") % request.env.user.display_name)
        return request.redirect('/my/workshop/order/%s' % repair.id)

    @http.route('/my/workshop/order/<int:repair_id>/checklist/pdf', type='http', auth='user', website=True)
    def workshop_checklist_pdf(self, repair_id, **kwargs):
        repair = self._get_repair(repair_id)
        if not repair.technical_checklist_line_ids:
            return request.redirect('/my/workshop/order/%s' % repair.id)
        report = request.env['ir.actions.report'].sudo()._get_report(
            'car_repair_industry.fleet_repair_technical_checklist_document'
        )
        if not report:
            raise UserError(_("No se encontró el reporte de checklist técnico."))
        today = fields.Date.today()
        data = {
            'lang': request.env.lang,
            'today_date': today.strftime('%d/%m/%Y'),
        }
        pdf_content, content_type = report._render_qweb_pdf(
            report.report_name, [repair.id], data=data
        )
        pdf_content = pdf_content and pdf_content[0] if isinstance(pdf_content, tuple) else pdf_content
        sequence = repair.sequence or repair.display_name or f'orden-{repair.id}'
        safe_sequence = ''.join(c if c.isalnum() or c in '-_' else '_' for c in str(sequence))
        filename = f'checklist-tecnico-{safe_sequence}.pdf'
        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf_content)),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
            ],
        )

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

    @http.route('/my/workshop/order/<int:repair_id>/technician/photos', type='http', auth='user', website=True, methods=['POST'])
    def workshop_technician_photos(self, repair_id, **post):
        repair = self._get_repair(repair_id)
        if not (self._is_technician() or self._is_internal_manager()):
            return request.render('car_repair_industry.portal_workshop_forbidden', {})

        Repair = request.env['fleet.repair'].sudo()
        validated_files = []
        uploads = request.httprequest.files.getlist('technician_photos')
        categories = request.httprequest.form.getlist('tech_photo_category')
        evidence_categories = {'externa', 'interna', 'dano_existente', 'pertenencias', 'documentos', 'otro'}
        for index, upload in enumerate(uploads):
            if not upload or not upload.filename:
                continue
            file_data = Repair._drive_prepare_image_file(
                upload.filename,
                upload.read(),
                mimetype=upload.mimetype,
            )
            category = categories[index] if index < len(categories) else 'otro'
            file_data['evidence_category'] = category if category in evidence_categories else 'otro'
            validated_files.append(file_data)

        if validated_files:
            evidence_type = post.get('evidence_type') or 'diagnostico'
            if evidence_type not in {'diagnostico', 'reparacion', 'entrega', 'otro'}:
                evidence_type = 'diagnostico'
            description = post.get('photo_description') or repair.service_detail or ''
            repair._drive_upload_evidence_images(
                self._rename_reception_photo_files(repair, validated_files),
                evidence_type=evidence_type,
                description=description,
            )
            repair.message_post(body=_("Subida de %s foto(s) de tipo '%s' desde portal por %s.") % (
                len(validated_files), evidence_type, request.env.user.display_name))
        return request.redirect('/my/workshop/order/%s' % repair.id)

    # ─── Solicitud de repuestos ────────────────────────────────────────────────

    @http.route('/my/workshop/spare-catalog', type='http', auth='user', website=True, methods=['GET'])
    def workshop_spare_catalog(self, q='', **kwargs):
        if not self._is_technician():
            return request.make_response(
                json.dumps({'error': 'forbidden'}),
                headers=[('Content-Type', 'application/json')],
                status=403,
            )
        q = (q or '').strip()
        if len(q) < 2:
            return request.make_response(
                json.dumps([]),
                headers=[('Content-Type', 'application/json')],
            )
        results = request.env['fleet.repair.spare.catalog'].sudo().search(
            [('name', 'ilike', q), ('active', '=', True)],
            order='name asc',
            limit=25,
        )
        data = [{'id': r.id, 'name': r.name} for r in results]
        return request.make_response(
            json.dumps(data),
            headers=[('Content-Type', 'application/json')],
        )

    @http.route(
        '/my/workshop/order/<int:repair_id>/spares/submit',
        type='http', auth='user', website=True, methods=['POST'],
        csrf=True,
    )
    def workshop_spare_submit(self, repair_id, **post):
        if not self._is_technician():
            return request.make_response(
                json.dumps({'error': 'forbidden'}),
                headers=[('Content-Type', 'application/json')],
                status=403,
            )

        try:
            repair = self._get_repair(repair_id)
        except (AccessError, MissingError) as exc:
            return request.make_response(
                json.dumps({'error': str(exc)}),
                headers=[('Content-Type', 'application/json')],
                status=403,
            )

        # Parse lines sent as JSON in the "lines" field
        try:
            raw_lines = json.loads(post.get('lines') or '[]')
        except (ValueError, TypeError):
            return request.make_response(
                json.dumps({'error': _('Formato de líneas inválido.')}),
                headers=[('Content-Type', 'application/json')],
                status=400,
            )

        if not isinstance(raw_lines, list) or not raw_lines:
            return request.make_response(
                json.dumps({'error': _('Debe agregar al menos un repuesto.')}),
                headers=[('Content-Type', 'application/json')],
                status=400,
            )

        # Validate each line before any write — use user's own env (portal has read access)
        Catalog = request.env['fleet.repair.spare.catalog']
        validated_lines = []
        for item in raw_lines:
            if not isinstance(item, dict):
                continue
            try:
                catalog_id = int(item.get('catalog_id') or 0)
                qty = float(item.get('quantity') or 0)
            except (ValueError, TypeError):
                return request.make_response(
                    json.dumps({'error': _('Datos de línea inválidos.')}),
                    headers=[('Content-Type', 'application/json')],
                    status=400,
                )
            if catalog_id <= 0:
                return request.make_response(
                    json.dumps({'error': _('Repuesto no válido.')}),
                    headers=[('Content-Type', 'application/json')],
                    status=400,
                )
            if qty <= 0:
                return request.make_response(
                    json.dumps({'error': _('La cantidad debe ser mayor que cero.')}),
                    headers=[('Content-Type', 'application/json')],
                    status=400,
                )
            catalog_item = Catalog.search([('id', '=', catalog_id), ('active', '=', True)], limit=1)
            if not catalog_item:
                return request.make_response(
                    json.dumps({'error': _('Repuesto no encontrado en el catálogo.')}),
                    headers=[('Content-Type', 'application/json')],
                    status=400,
                )
            note = (item.get('note') or '').strip()[:500]
            validated_lines.append({
                'spare_catalog_id': catalog_item.id,
                'quantity': qty,
                'technician_note': note or False,
            })

        if not validated_lines:
            return request.make_response(
                json.dumps({'error': _('Debe agregar al menos un repuesto válido.')}),
                headers=[('Content-Type', 'application/json')],
                status=400,
            )

        # All validations passed — create with sudo()
        SpareRequest = request.env['fleet.repair.spare.request'].sudo()
        SpareRequestLine = request.env['fleet.repair.spare.request.line'].sudo()

        spare_request = SpareRequest.create({
            'repair_id': repair.id,
            'requested_by_id': request.env.user.id,
            'company_id': request.env.company.id,
        })
        for line_vals in validated_lines:
            line_vals['request_id'] = spare_request.id
            SpareRequestLine.create(line_vals)

        spare_request.message_post(
            body=_("Solicitud de repuestos enviada desde portal por %s.") % request.env.user.display_name
        )

        return request.make_response(
            json.dumps({'ok': True, 'request_id': spare_request.id}),
            headers=[('Content-Type', 'application/json')],
        )
