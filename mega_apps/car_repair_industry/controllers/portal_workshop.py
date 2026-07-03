# -*- coding: utf-8 -*-

import json
import re
from odoo import _, fields, http
from pathlib import Path

from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

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

    _CO_DOC_NAME_MAP = {
        'rut': 'NIT',
        'national_citizen_id': 'Cédula de ciudadanía',
    }

    def _get_colombia_partner_defaults(self, doc_type_code=None):
        """Return localization fields for Colombia partners.
        doc_type_code: 'national_citizen_id' | 'rut' | None
        """
        env = request.env
        country_co = env['res.country'].sudo().search([('code', '=', 'CO')], limit=1)
        state_ant = env['res.country.state'].sudo().search([
            ('country_id', '=', country_co.id),
            ('name', 'ilike', 'Antioquia'),
        ], limit=1)
        vals = {
            'country_id': country_co.id if country_co else False,
            'state_id': state_ant.id if state_ant else False,
            'city': 'Medellín',
        }
        if doc_type_code:
            IdType = env['l10n_latam.identification.type'].sudo()
            id_type = IdType.search([('l10n_co_document_code', '=', doc_type_code)], limit=1)
            if not id_type:
                display_name = self._CO_DOC_NAME_MAP.get(doc_type_code, '')
                if display_name and country_co:
                    id_type = IdType.search([
                        ('name', 'ilike', display_name),
                        ('country_id', '=', country_co.id),
                    ], limit=1)
            if id_type:
                vals['l10n_latam_identification_type_id'] = id_type.id
        return vals

    _DIAN_VIA_CODES = {
        'CL', 'CR', 'AV', 'AC', 'AK', 'DG', 'TV', 'AUT', 'CRT',
        'KM', 'VRD', 'URB', 'BRR', 'MZ', 'PQ',
    }
    _DIAN_COMP_CODES = {
        'AP', 'OF', 'LC', 'TO', 'BL', 'IN', 'P', 'ED', 'CA', 'CC',
        'CON', 'BG', 'PH', 'DPTO', 'SUR', 'AG', 'ZF',
    }

    def _build_dian_street(self, post):
        """Build a DIAN-formatted street string from portal POST fields.
        Returns the street string or False if required fields are missing.
        """
        def clean(val, allow_slash=False):
            pattern = r'[^A-Za-z0-9\s\-]' if not allow_slash else r'[^A-Za-z0-9\s\-/]'
            return re.sub(pattern, '', (val or '').strip()).upper()

        via_tipo   = clean(post.get('addr_via_tipo',  '')).split()[0] if post.get('addr_via_tipo') else ''
        via_num    = clean(post.get('addr_via_num',   ''))
        cruce      = clean(post.get('addr_cruce',     ''))
        placa      = clean(post.get('addr_placa',     ''))
        comp_tipo  = clean(post.get('addr_comp_tipo', '')).split()[0] if post.get('addr_comp_tipo') else ''
        comp_num   = clean(post.get('addr_comp_num',  ''))

        if not (via_tipo and via_num and cruce and placa):
            return False

        parts = [via_tipo, via_num, cruce, placa]
        if comp_tipo:
            parts.append(comp_tipo)
        if comp_num:
            parts.append(comp_num)
        return ' '.join(parts)

    def _build_nit_vat(self, post, is_nit):
        """Return (vat_to_store, nit_digits_only) from POST data.
        For NIT: validates 9 digits + 1 DV, returns ('NNNNNNNNN-D', 'NNNNNNNNN').
        For others: returns (cleaned_vat, cleaned_vat).
        Raises UserError on invalid NIT format.
        """
        if is_nit:
            raw_digits = re.sub(r'\D', '', (post.get('client_vat') or ''))
            raw_dv     = re.sub(r'\D', '', (post.get('client_dv') or ''))
            if raw_digits and len(raw_digits) != 9:
                raise UserError(_("El NIT debe tener exactamente 9 dígitos."))
            if raw_digits and (not raw_dv or len(raw_dv) != 1):
                raise UserError(_("El código de verificación (DV) es obligatorio y debe ser 1 dígito."))
            vat = f"{raw_digits}-{raw_dv}" if raw_digits and raw_dv else (raw_digits or False)
            return vat, raw_digits
        else:
            vat = re.sub(r'\s+', '', (post.get('client_vat') or '')).upper() or False
            return vat, vat

    def _is_internal_manager(self):
        return (
            request.env.user.has_group('car_repair_industry.group_fleet_repair_service_manager')
            or request.env.user.has_group('car_repair_industry.group_fleet_repair_directeur_commercial')
            or request.env.user.has_group('base.group_system')
        )

    def _portal_domain(self):
        user = request.env.user
        if self._is_internal_manager() or self._is_advisor():
            return []
        domains = []
        if self._is_technician():
            domains.append(('portal_technician_id', '=', user.id))
        if self._is_road_test():
            domains.append(('road_test_user_id', '=', user.id))
            road_test_repair_ids = request.env['fleet.road.test'].sudo().search(
                [('driver_id', '=', user.id)]
            ).mapped('repair_id.id')
            if road_test_repair_ids:
                domains.append(('id', 'in', road_test_repair_ids))
        if not domains:
            return [('id', '=', 0)]
        if len(domains) == 1:
            return domains[0:1]
        domain = ['|'] * (len(domains) - 1)
        for item in domains:
            domain.append(item)
        return domain

    def _get_repair(self, repair_id):
        repair = request.env['fleet.repair'].sudo().browse(repair_id)
        if not repair.exists():
            raise MissingError(_("La orden no existe."))
        allowed = self._is_internal_manager() or self._is_advisor()
        user = request.env.user
        allowed = allowed or (self._is_technician() and repair.portal_technician_id.id == user.id)
        allowed = allowed or (self._is_road_test() and repair.road_test_user_id.id == user.id)
        if not allowed and self._is_road_test():
            allowed = bool(repair.road_test_ids.filtered(lambda rt: rt.driver_id.id == user.id))
        if not allowed:
            raise AccessError(_("No tiene acceso a esta orden."))
        return repair

    # Each entry: (field, operator, value)
    FILTER_STATE_MAP = {
        'to_assign': ('service_flow_state', '=',  'to_assign'),
        'assigned':  ('service_flow_state', '=',  'assigned'),
        'diagnosis': ('state',              '=',  'diagnosis'),
        'road_test': ('service_flow_state', 'in', ('road_test_requested', 'road_test')),
        'purchase':  ('service_flow_state', '=',  'purchase_requested'),
    }

    SEDE_MAP = {
        'renting':    ('customer_type', '=', 'renting'),
        'particular': ('customer_type', '=', 'particular'),
        'corporate':  ('customer_type', '=', 'corporate'),
    }

    def _dashboard_values(self, active_filter='all', search='', page=1, active_sede='all'):
        Repair = request.env['fleet.repair'].sudo()
        base_domain = self._portal_domain()

        # Sede filter narrows the base domain for both stats and results
        sede_domain = list(base_domain)
        if active_sede in self.SEDE_MAP:
            sede_domain.append(self.SEDE_MAP[active_sede])

        # State filter applied on top of sede domain
        filter_domain = list(sede_domain)
        if active_filter in self.FILTER_STATE_MAP:
            filter_domain.append(self.FILTER_STATE_MAP[active_filter])

        # Search applied on top of filter domain
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
        if active_sede != 'all':
            url_args['sede'] = active_sede
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

        # Stats reflect sede filter but not state filter (so counts update per sede)
        stats = {
            'total':     Repair.search_count(sede_domain),
            'to_assign': Repair.search_count(sede_domain + [('service_flow_state', '=', 'to_assign')]),
            'assigned':  Repair.search_count(sede_domain + [('service_flow_state', '=', 'assigned')]),
            'diagnosis': Repair.search_count(sede_domain + [('state', '=', 'diagnosis')]),
            'road_test': Repair.search_count(sede_domain + [('service_flow_state', 'in', ['road_test_requested', 'road_test'])]),
            'purchase':  Repair.search_count(sede_domain + [('service_flow_state', '=', 'purchase_requested')]),
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
            'active_sede': active_sede,
            'stats': stats,
        }

    @http.route(
        ['/my/workshop', '/my/workshop/orders', '/my/workshop/page/<int:page>'],
        type='http', auth='user', website=True,
    )
    def workshop_dashboard(self, filter=None, search='', page=1, sede=None, **kwargs):
        active_filter = filter if filter in self.FILTER_STATE_MAP else 'all'
        active_sede = sede if sede in self.SEDE_MAP else 'all'
        search = (search or '').strip()
        try:
            page = max(1, int(page))
        except (TypeError, ValueError):
            page = 1
        return request.render(
            'car_repair_industry.portal_workshop_dashboard',
            self._dashboard_values(active_filter, search, page, active_sede),
        )

    @http.route('/my/workshop/order/new', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def workshop_order_new(self, **post):
        if not (self._is_advisor() or self._is_internal_manager()):
            return request.render('car_repair_industry.portal_workshop_forbidden', {})

        Template = request.env['fleet.repair.reception.checklist.template'].sudo()
        VehicleModel = request.env['fleet.vehicle.model'].sudo()
        VehicleBrand = request.env['fleet.vehicle.model.brand'].sudo()
        templates = Template.search([('active', '=', True)], order='name')
        vehicle_models = VehicleModel.search([], order='name')
        vehicle_brands = VehicleBrand.search([], order='name')
        renting_partner = request.env['fleet.repair'].sudo()._find_renting_partner()
        selected_template = Template.browse(int(post.get('template_id') or 0)) if post.get('template_id') else templates[:1]

        if request.httprequest.method == 'POST':
            validated_files = self._prepare_reception_photo_files()
            repair = self._create_portal_repair(post, selected_template, validated_files)
            return request.redirect('/my/workshop/order/%s/created' % repair.id)

        return request.render('car_repair_industry.portal_workshop_order_form', {
            'templates': templates,
            'selected_template': selected_template,
            'vehicle_models': vehicle_models,
            'vehicle_brands': vehicle_brands,
            'renting_partner': renting_partner,
        })

    @http.route('/my/workshop/partner-lookup', type='http', auth='user', website=True, methods=['GET'])
    def workshop_partner_lookup(self, vat='', doc_type='', dv='', **kwargs):
        if not (self._is_advisor() or self._is_internal_manager()):
            return request.make_response(
                json.dumps({'found': False}),
                headers=[('Content-Type', 'application/json')],
            )
        is_nit = doc_type == 'nit'
        if is_nit:
            nit_digits = re.sub(r'\D', '', vat or '')
            dv_digit = re.sub(r'\D', '', dv or '')
            if len(nit_digits) < 3:
                return request.make_response(
                    json.dumps({'found': False}),
                    headers=[('Content-Type', 'application/json')],
                )
            search_terms = [nit_digits]
            if dv_digit:
                search_terms.append(f"{nit_digits}-{dv_digit}")
            if len(search_terms) == 1:
                domain = [('vat', 'ilike', nit_digits), ('is_company', '=', True)]
            else:
                domain = ['&', '|',
                          ('vat', 'ilike', search_terms[0]),
                          ('vat', 'ilike', search_terms[1]),
                          ('is_company', '=', True)]
        else:
            vat_clean = (vat or '').strip().upper()
            if len(vat_clean) < 3:
                return request.make_response(
                    json.dumps({'found': False}),
                    headers=[('Content-Type', 'application/json')],
                )
            domain = [('vat', '=ilike', vat_clean), ('is_company', '=', False)]
        partner = request.env['res.partner'].sudo().search(domain, limit=1)
        if not partner:
            return request.make_response(
                json.dumps({'found': False}),
                headers=[('Content-Type', 'application/json')],
            )
        # Extract DV from stored NIT (format: "NNNNNNNNN-D" or "NNN.NNN.NNN-D")
        stored_dv = ''
        if is_nit and partner.vat:
            match = re.search(r'-(\d)$', partner.vat.strip())
            if match:
                stored_dv = match.group(1)
        return request.make_response(
            json.dumps({
                'found': True,
                'name': partner.name or '',
                'phone': partner.phone or partner.mobile or '',
                'email': partner.email or '',
                'dv': stored_dv,
            }),
            headers=[('Content-Type', 'application/json')],
        )

    @http.route('/my/workshop/vehicle-lookup', type='http', auth='user', website=True, methods=['GET'])
    def workshop_vehicle_lookup(self, plate='', **kwargs):
        if not (self._is_advisor() or self._is_internal_manager()):
            return request.make_response(
                json.dumps({'found': False}),
                headers=[('Content-Type', 'application/json')],
            )
        plate = (plate or '').strip().upper()
        if len(plate) < 4:
            return request.make_response(
                json.dumps({'found': False}),
                headers=[('Content-Type', 'application/json')],
            )

        # Buscar en órdenes anteriores (fuente más completa para este taller)
        repair = request.env['fleet.repair'].sudo().search(
            [('license_plate', '=ilike', plate)],
            order='create_date desc',
            limit=1,
        )
        if repair:
            return request.make_response(
                json.dumps({
                    'found': True,
                    'source': 'repair',
                    'brand_id': repair.vehicle_brand_id.id or 0,
                    'brand_name': repair.vehicle_brand_id.name or '',
                    'model_id': repair.model_id.id or 0,
                    'model_name': repair.model_id.name or '',
                    'model_year': repair.model_year or '',
                    'engine_displacement': repair.engine_displacement or '',
                    'engine_number': repair.engine_number or '',
                    'vin_sn': repair.vin_sn or '',
                    'fuel_type': repair.fuel_type or '',
                }),
                headers=[('Content-Type', 'application/json')],
            )

        # Buscar en flota de vehículos
        vehicle = request.env['fleet.vehicle'].sudo().search(
            [('license_plate', '=ilike', plate)],
            limit=1,
        )
        if vehicle:
            return request.make_response(
                json.dumps({
                    'found': True,
                    'source': 'fleet',
                    'brand_id': vehicle.model_id.brand_id.id or 0,
                    'brand_name': vehicle.model_id.brand_id.name or '',
                    'model_id': vehicle.model_id.id or 0,
                    'model_name': vehicle.model_id.name or '',
                    'model_year': vehicle.model_year or '',
                    'engine_displacement': '',
                    'engine_number': getattr(vehicle, 'engine_number', '') or '',
                    'vin_sn': vehicle.vin_sn or '',
                    'fuel_type': vehicle.fuel_type or '',
                }),
                headers=[('Content-Type', 'application/json')],
            )

        return request.make_response(
            json.dumps({'found': False}),
            headers=[('Content-Type', 'application/json')],
        )

    @http.route('/my/workshop/service-search', type='http', auth='user', website=True, methods=['GET'])
    def workshop_service_search(self, q='', **kwargs):
        if not (self._is_advisor() or self._is_internal_manager()):
            return request.make_response(
                json.dumps([]),
                headers=[('Content-Type', 'application/json')],
            )
        q = (q or '').strip()
        domain = [('name', 'ilike', q)] if q else []
        results = request.env['service.type'].sudo().search(
            domain, order='name asc', limit=15
        )
        data = [{'id': r.id, 'name': r.name} for r in results]
        return request.make_response(
            json.dumps(data),
            headers=[('Content-Type', 'application/json')],
        )

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
        delivered_by_email = (post.get('delivered_by_email') or '').strip()

        if customer_type == 'renting':
            renting_mode = (post.get('renting_mode') or 'billing').strip()
            if renting_mode == 'client':
                if not client_name:
                    raise UserError(_("Para Cliente de Renting debe registrar el nombre del conductor."))
                client_doc_type = (post.get('client_doc_type') or 'cedula').strip()
                is_nit = client_doc_type == 'nit'
                co_doc_code = 'rut' if is_nit else 'national_citizen_id'
                client_vat, nit_digits = self._build_nit_vat(post, is_nit)
                partner = Partner.browse()
                if client_vat:
                    if is_nit:
                        partner = Partner.search([
                            ('vat', 'ilike', nit_digits),
                            ('is_company', '=', True),
                        ], limit=1)
                    else:
                        partner = Partner.search([
                            ('vat', '=ilike', client_vat),
                            ('is_company', '=', False),
                        ], limit=1)
                co_defaults = self._get_colombia_partner_defaults(co_doc_code)
                dian_street = self._build_dian_street(post)
                if not dian_street:
                    raise UserError(_("La dirección es obligatoria. Complete tipo de vía, número, cruce y placa."))
                if not partner:
                    partner = Partner.create({
                        'name': client_name,
                        'vat': client_vat or False,
                        'phone': client_phone,
                        'mobile': client_phone,
                        'email': client_email,
                        'is_company': is_nit,
                        'company_type': 'company' if is_nit else 'person',
                        'street': dian_street,
                        **co_defaults,
                    })
                elif not partner.street:
                    partner.write({'street': dian_street})
                contact_name = delivered_by_name or client_name
                contact_phone = delivered_by_phone or client_phone
            else:
                partner = Repair._get_renting_partner()
                if not delivered_by_name or not delivered_by_phone:
                    raise UserError(_("Para Renting debe registrar nombre y celular de quien entrega el vehículo."))
                client_phone = partner.phone or partner.mobile or ''
                client_email = partner.email or ''
                contact_name = delivered_by_name
                contact_phone = delivered_by_phone
        elif customer_type == 'corporate':
            # MegaSur uses the same fields as particular (persons or companies)
            if not client_name:
                raise UserError(_("Debe registrar el nombre del cliente."))
            client_doc_type = (post.get('client_doc_type') or 'cedula').strip()
            is_nit = client_doc_type == 'nit'
            co_doc_code = 'rut' if is_nit else 'national_citizen_id'
            client_vat, nit_digits = self._build_nit_vat(post, is_nit)
            partner = Partner.browse()
            if client_vat:
                if is_nit:
                    partner = Partner.search([
                        ('vat', 'ilike', nit_digits),
                        ('is_company', '=', True),
                    ], limit=1)
                else:
                    partner = Partner.search([
                        ('vat', '=ilike', client_vat),
                        ('is_company', '=', False),
                    ], limit=1)
            co_defaults = self._get_colombia_partner_defaults(co_doc_code)
            dian_street = self._build_dian_street(post)
            if not dian_street:
                raise UserError(_("La dirección es obligatoria. Complete tipo de vía, número, cruce y placa."))
            if not partner:
                partner = Partner.create({
                    'name': client_name,
                    'vat': client_vat or False,
                    'phone': client_phone,
                    'mobile': client_phone,
                    'email': client_email,
                    'is_company': is_nit,
                    'company_type': 'company' if is_nit else 'person',
                    'street': dian_street,
                    **co_defaults,
                })
            elif not partner.street:
                partner.write({'street': dian_street})
            contact_name = delivered_by_name or client_name
            contact_phone = delivered_by_phone or client_phone
        else:
            if not client_name:
                raise UserError(_("Debe registrar el nombre del cliente particular."))
            client_doc_type = (post.get('client_doc_type') or 'cedula').strip()
            is_nit = client_doc_type == 'nit'
            co_doc_code = 'rut' if is_nit else 'national_citizen_id'
            client_vat, nit_digits = self._build_nit_vat(post, is_nit)
            partner = Partner.browse()
            if client_vat:
                if is_nit:
                    partner = Partner.search([
                        ('vat', 'ilike', nit_digits),
                        ('is_company', '=', True),
                    ], limit=1)
                else:
                    partner = Partner.search([
                        ('vat', '=ilike', client_vat),
                        ('is_company', '=', False),
                    ], limit=1)
            co_defaults = self._get_colombia_partner_defaults(co_doc_code)
            dian_street = self._build_dian_street(post)
            if not dian_street:
                raise UserError(_("La dirección es obligatoria. Complete tipo de vía, número, cruce y placa."))
            if not partner:
                partner = Partner.create({
                    'name': client_name,
                    'vat': client_vat or False,
                    'phone': client_phone,
                    'mobile': client_phone,
                    'email': client_email,
                    'is_company': is_nit,
                    'company_type': 'company' if is_nit else 'person',
                    'street': dian_street,
                    **co_defaults,
                })
            elif not partner.street:
                partner.write({'street': dian_street})
            contact_name = delivered_by_name or client_name
            contact_phone = delivered_by_phone or client_phone

        service_type_ids = []
        raw_service_types = request.httprequest.form.getlist('service_types')
        for raw in raw_service_types:
            try:
                service_type_ids.append(int(raw))
            except (TypeError, ValueError):
                continue

        ServiceTypeModel = request.env['service.type'].sudo()
        for raw_name in request.httprequest.form.getlist('new_service_names'):
            name = (raw_name or '').strip()
            if not name:
                continue
            existing = ServiceTypeModel.search([('name', '=ilike', name)], limit=1)
            if existing:
                if existing.id not in service_type_ids:
                    service_type_ids.append(existing.id)
            else:
                try:
                    with request.env.cr.savepoint():
                        new_st = ServiceTypeModel.create({'name': name})
                    service_type_ids.append(new_st.id)
                except Exception:
                    # Race condition: another concurrent request created the same
                    # service type between our search and our insert.
                    # Re-search and reuse the existing record.
                    fallback = ServiceTypeModel.search([('name', '=ilike', name)], limit=1)
                    if fallback:
                        if fallback.id not in service_type_ids:
                            service_type_ids.append(fallback.id)
                    else:
                        raise

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

    @http.route('/my/workshop/order/<int:repair_id>/created', type='http', auth='user', website=True)
    def workshop_order_created(self, repair_id, **kwargs):
        try:
            repair = self._get_repair(repair_id)
        except (AccessError, MissingError):
            return request.render('car_repair_industry.portal_workshop_forbidden', {})
        if not (self._is_advisor() or self._is_internal_manager()):
            return request.render('car_repair_industry.portal_workshop_forbidden', {})
        return request.render('car_repair_industry.portal_workshop_order_created', {
            'repair': repair,
        })

    @http.route('/my/workshop/order/<int:repair_id>/reception-pdf', type='http', auth='user', website=True)
    def workshop_order_reception_pdf(self, repair_id, **kwargs):
        try:
            repair = self._get_repair(repair_id)
        except (AccessError, MissingError):
            return request.render('car_repair_industry.portal_workshop_forbidden', {})
        if not (self._is_advisor() or self._is_internal_manager()):
            return request.render('car_repair_industry.portal_workshop_forbidden', {})
        pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'car_repair_industry.report_car_repair_reception_act', [repair.id]
        )
        filename = 'Acta_Recepcion_%s.pdf' % (repair.sequence or str(repair.id))
        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', 'attachment; filename="%s"' % filename),
            ],
        )

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
                # Sync to the diagnosis copy (created when diagnosis was opened from backend)
                diag_copies = RepairLine.search([('source_line_id', '=', line.id)])
                if diag_copies:
                    diag_copies.write(write_vals)

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
            try:
                with request.env.cr.savepoint():
                    repair.message_post(body=_("Avance técnico guardado por %s.") % request.env.user.display_name)
            except Exception:
                pass
        return request.redirect('/my/workshop/order/%s' % repair.id)

    # ── Rutas JSON-RPC (sin recarga de página) ─────────────────────────────

    @http.route('/my/workshop/order/<int:repair_id>/technician/save', type='json', auth='user', website=True)
    def workshop_technician_save(self, repair_id, technical_observation='', requested_materials='', services=None, **kw):
        try:
            repair = self._get_repair(repair_id)
        except (AccessError, MissingError):
            return {'error': 'forbidden'}
        if not (self._is_technician() or self._is_internal_manager()):
            return {'error': 'forbidden'}

        repair.sudo().write({
            'technical_observation': technical_observation or False,
            'requested_materials': requested_materials or False,
        })

        RepairLine = request.env['fleet.repair.line'].sudo()
        allowed_statuses = {'pendiente', 'en_progreso', 'completado'}
        for svc in (services or []):
            try:
                line = RepairLine.browse(int(svc.get('id') or 0))
            except (TypeError, ValueError):
                continue
            if not line.exists() or line.fleet_repair_id.id != repair.id:
                continue
            write_vals = {}
            if svc.get('status') in allowed_statuses:
                write_vals['tecnico_status'] = svc['status']
            if 'notes' in svc:
                write_vals['tecnico_notes'] = svc.get('notes') or False
            if write_vals:
                line.write(write_vals)
                diag_copies = RepairLine.search([('source_line_id', '=', line.id)])
                if diag_copies:
                    diag_copies.write(write_vals)

        return {'ok': True}

    @http.route('/my/workshop/order/<int:repair_id>/checklist/save', type='json', auth='user', website=True)
    def workshop_checklist_save(self, repair_id, lines=None, **kw):
        try:
            repair = self._get_repair(repair_id)
        except (AccessError, MissingError):
            return {'error': 'forbidden'}
        if not (self._is_technician() or self._is_internal_manager()):
            return {'error': 'forbidden'}

        ChecklistLine = request.env['fleet.repair.reception.checklist.line'].sudo()
        allowed_states = {'good', 'regular', 'bad', 'not_apply'}
        allowed_repaired = {'yes', 'no', 'pending'}
        for item in (lines or []):
            try:
                line = ChecklistLine.browse(int(item.get('id') or 0))
            except (TypeError, ValueError):
                continue
            if not line.exists() or line.repair_id.id != repair.id:
                continue
            write_vals = {}
            if item.get('state') in allowed_states:
                write_vals['state'] = item['state']
            if 'observation' in item:
                write_vals['observation'] = item.get('observation') or False
            if item.get('repaired') in allowed_repaired:
                write_vals['repaired'] = item['repaired']
            if 'measurement_left' in item:
                write_vals['measurement_left'] = item.get('measurement_left') or False
            if 'measurement_right' in item:
                write_vals['measurement_right'] = item.get('measurement_right') or False
            if 'position' in item:
                write_vals['position'] = item.get('position') or False
            if item.get('expiration_date'):
                try:
                    from datetime import datetime
                    write_vals['expiration_date'] = datetime.strptime(item['expiration_date'], '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass
            if write_vals:
                line.write(write_vals)

        return {'ok': True}

    @http.route('/my/workshop/order/<int:repair_id>/road-test/request', type='http', auth='user', website=True, methods=['POST'])
    def workshop_road_test_request(self, repair_id, **post):
        try:
            repair = self._get_repair(repair_id)
        except (AccessError, MissingError):
            return request.render('car_repair_industry.portal_workshop_forbidden', {})
        if not (self._is_advisor() or self._is_technician() or self._is_internal_manager()):
            return request.render('car_repair_industry.portal_workshop_forbidden', {})
        test_type = post.get('test_type', 'after')
        if test_type not in ('before', 'during', 'after'):
            test_type = 'after'
        request.env['fleet.road.test'].sudo().create({
            'repair_id': repair.id,
            'test_type': test_type,
            'request_observation': (post.get('request_observation') or '').strip() or False,
            'requested_by_id': request.env.user.id,
        })
        return request.redirect('/my/workshop/order/%s' % repair_id)

    @http.route('/my/workshop/order/<int:repair_id>/road-test/<int:test_id>/update', type='http', auth='user', website=True, methods=['POST'])
    def workshop_road_test_test_update(self, repair_id, test_id, **post):
        try:
            repair = self._get_repair(repair_id)
        except (AccessError, MissingError):
            return request.render('car_repair_industry.portal_workshop_forbidden', {})
        if not (self._is_road_test() or self._is_internal_manager()):
            return request.render('car_repair_industry.portal_workshop_forbidden', {})
        road_test = request.env['fleet.road.test'].sudo().browse(test_id)
        if not road_test.exists() or road_test.repair_id.id != repair_id:
            return request.render('car_repair_industry.portal_workshop_forbidden', {})
        user = request.env.user
        if not (self._is_internal_manager() or road_test.driver_id.id == user.id):
            return request.render('car_repair_industry.portal_workshop_forbidden', {})

        vals = {}
        result_val = (post.get('result') or '').strip()
        if result_val:
            vals['result'] = result_val
        final_obs = (post.get('final_observations') or '').strip()
        if final_obs:
            vals['final_observations'] = final_obs
        try:
            km_start = float(post.get('km_start') or 0)
            if km_start > 0:
                vals['km_start'] = km_start
        except (ValueError, TypeError):
            pass
        try:
            km_end = float(post.get('km_end') or 0)
            if km_end > 0:
                vals['km_end'] = km_end
        except (ValueError, TypeError):
            pass

        action = post.get('action')
        if action == 'start' and road_test.state == 'assigned':
            vals['state'] = 'in_progress'
        elif action == 'done' and road_test.state == 'in_progress':
            vals['state'] = 'done'
            vals['completed_at'] = fields.Datetime.now()

        if vals:
            road_test.sudo().write(vals)

        return request.redirect('/my/workshop/order/%s' % repair_id)

    @http.route('/my/workshop/order/<int:repair_id>/road-test/save', type='json', auth='user', website=True)
    def workshop_road_test_save(self, repair_id, road_test_result='', action='finish', **kw):
        try:
            repair = self._get_repair(repair_id)
        except (AccessError, MissingError):
            return {'error': 'forbidden'}
        if not self._is_road_test():
            return {'error': 'forbidden'}

        repair.sudo().write({'road_test_result': road_test_result or False})
        if action == 'start':
            repair.sudo().action_flow_start_road_test()
        else:
            repair.sudo().action_flow_finish_road_test()

        return {'ok': True, 'reload': True}

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
        if not self._is_road_test():
            return request.render('car_repair_industry.portal_workshop_forbidden', {})
        repair.sudo().write({'road_test_result': post.get('road_test_result')})
        if post.get('action') == 'start':
            repair.sudo().action_flow_start_road_test()
        else:
            repair.sudo().action_flow_finish_road_test()
        return request.redirect('/my/workshop/order/%s' % repair.id)

    @http.route('/my/workshop/order/<int:repair_id>/services/add', type='json', auth='user', website=True, methods=['POST'])
    def workshop_add_service(self, repair_id, name='', **kw):
        if not (self._is_technician() or self._is_internal_manager()):
            return {'error': 'forbidden'}
        name = (name or '').strip()
        if not name:
            return {'error': 'empty'}
        repair = self._get_repair(repair_id)
        if not repair:
            return {'error': 'not_found'}

        ServiceType = request.env['service.type'].sudo()
        RepairLine = request.env['fleet.repair.line'].sudo()

        # Buscar tipo de servicio existente (sin distinguir mayúsculas)
        stype = ServiceType.search([('name', '=ilike', name)], limit=1)
        if not stype:
            stype = ServiceType.create({'name': name})
            is_new_type = True
        else:
            is_new_type = False

        # Verificar si ya está en la orden
        existing_line = RepairLine.search([
            ('fleet_repair_id', '=', repair.id),
            ('service_type', '=', stype.id),
        ], limit=1)
        if existing_line:
            return {
                'already_exists': True,
                'line_id': existing_line.id,
                'service_name': stype.name,
            }

        # Calcular próximo número de secuencia
        current_count = RepairLine.search_count([('fleet_repair_id', '=', repair.id)])

        line_state = repair.state if repair.state in ('draft', 'diagnosis', 'done') else 'diagnosis'
        line = RepairLine.create({
            'fleet_repair_id': repair.id,
            'diagnose_id': repair.diagnose_id.id or False,
            'license_plate': repair.license_plate,
            'model_id': repair.model_id.id or False,
            'vehicle_brand_id': repair.vehicle_brand_id.id or False,
            'model_year': repair.model_year or False,
            'engine_number': repair.engine_number or False,
            'vin_sn': repair.vin_sn or False,
            'fuel_type': repair.fuel_type or False,
            'service_type': stype.id,
            'tecnico_status': 'pendiente',
            'state': line_state,
        })
        return {
            'success': True,
            'line_id': line.id,
            'service_name': stype.name,
            'seq': current_count + 1,
            'is_new_type': is_new_type,
        }

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

    @http.route('/my/workshop/spares/line/remove', type='json', auth='user', website=True, methods=['POST'])
    def workshop_spare_line_remove(self, line_id=None, **kw):
        if not self._is_technician():
            return {'error': 'forbidden'}
        try:
            line_id = int(line_id or 0)
        except (ValueError, TypeError):
            return {'error': 'invalid'}
        if line_id <= 0:
            return {'error': 'invalid'}
        line = request.env['fleet.repair.spare.request.line'].sudo().search(
            [('id', '=', line_id)], limit=1
        )
        if not line:
            return {'error': 'not_found'}
        if line.request_id.state != 'requested':
            return {'error': 'not_editable', 'msg': 'Esta solicitud ya fue procesada y no se puede modificar.'}
        try:
            self._get_repair(line.request_id.repair_id.id)
        except Exception:
            return {'error': 'forbidden'}
        line.unlink()
        return {'ok': True}

    @http.route('/my/workshop/spares/line/add', type='json', auth='user', website=True, methods=['POST'])
    def workshop_spare_line_add(self, request_id=None, catalog_id=None, quantity=None, note='', **kw):
        if not self._is_technician():
            return {'error': 'forbidden'}
        try:
            request_id = int(request_id or 0)
            catalog_id = int(catalog_id or 0)
            qty = float(quantity or 0)
        except (ValueError, TypeError):
            return {'error': 'invalid'}
        if request_id <= 0 or catalog_id <= 0 or qty <= 0:
            return {'error': 'invalid_data'}
        spare_req = request.env['fleet.repair.spare.request'].sudo().search(
            [('id', '=', request_id)], limit=1
        )
        if not spare_req:
            return {'error': 'not_found'}
        if spare_req.state != 'requested':
            return {'error': 'not_editable', 'msg': 'Esta solicitud ya fue procesada.'}
        try:
            self._get_repair(spare_req.repair_id.id)
        except Exception:
            return {'error': 'forbidden'}
        catalog = request.env['fleet.repair.spare.catalog'].sudo().search(
            [('id', '=', catalog_id), ('active', '=', True)], limit=1
        )
        if not catalog:
            return {'error': 'catalog_not_found'}
        note_clean = (note or '').strip()[:500]
        line = request.env['fleet.repair.spare.request.line'].sudo().create({
            'request_id': spare_req.id,
            'spare_catalog_id': catalog.id,
            'quantity': qty,
            'technician_note': note_clean or False,
        })
        return {'ok': True, 'line_id': line.id, 'name': catalog.name, 'quantity': qty, 'note': note_clean}


_WORKSHOP_PORTAL_GROUPS = [
    'car_repair_industry.group_fleet_repair_portal_advisor',
    'car_repair_industry.group_fleet_repair_portal_technician',
    'car_repair_industry.group_fleet_repair_portal_road_test',
    'car_repair_industry.group_fleet_repair_service_manager',
    'car_repair_industry.group_fleet_repair_directeur_commercial',
]


class WorkshopPortalHome(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if not counters:
            values['is_workshop_user'] = True
        return values

    @http.route(['/my', '/my/home'], type='http', auth='user', website=True)
    def home(self, **kw):
        user = request.env.user
        is_workshop = any(user.has_group(g) for g in _WORKSHOP_PORTAL_GROUPS)
        if is_workshop:
            return request.redirect('/my/workshop')
        return super().home(**kw)
