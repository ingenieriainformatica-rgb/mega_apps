

import requests
import random
from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api, _
from odoo.addons.industry_real_estate import const
import math
from collections import defaultdict
from odoo.tools.float_utils import float_round, float_compare
from odoo.addons.industry_real_estate import const
from decimal import Decimal, ROUND_HALF_UP
import logging
_logger = logging.getLogger(__name__)

class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    
    # Consecutivo del inmueble (sin mostrar en vista por ahora)
    x_cons_inm = fields.Char(
        string='Consecutivo Inmueble',
        index=True,
        copy=False,
        help='Identificador único del inmueble traído desde Excel (Cons_Inm).',
    )

    @api.constrains('x_cons_inm', 'x_is_property')
    def _check_cons_inm_unique(self):
        """Unicidad lógica: sólo aplica a propiedades y sólo si viene informado."""
        for rec in self:
            if rec.x_is_property and rec.x_cons_inm:
                dup = self.search_count([
                    ('id', '!=', rec.id),
                    ('x_is_property', '=', True),
                    ('x_cons_inm', '=', rec.x_cons_inm),
                ])
                if dup:
                    _logger.warning("Ya existe otra propiedad con el consecutivo %s." % rec.x_cons_inm)
    
    # Coordenadas (si las usas después)
    x_latitude = fields.Float(string='Latitud')
    x_longitude = fields.Float(string='Longitud')

    # Campo HTML que simula el mapa para presentación
    x_dummy_map = fields.Html(
        string="Mapa (simulado)",
        compute="_compute_dummy_map",
        sanitize=False
    )
    
    name = fields.Char(string='Nombre de la propiedad', required=True, index=True)
    
    x_product_tmpl_id = fields.Many2one('product.template', compute='_compute_x_product', store=True)
    
    plan_id = fields.Many2one(
        'account.analytic.plan',
        string="Plan",
        required=True,  
        default=lambda self: self.env['account.analytic.plan'].search([('name','=','Properties')], limit=1)
    )

    x_property_registration_id = fields.Char(
        string='Matrícula inmobiliaria',
        help="Número de matricula (Impuesto predial - Cert. de tradición y libertad)",
        index= True
    )

    # Compatible con Odoo 18 y 19
    try:
        # Odoo 19: Nueva sintaxis con models.Constraint
        _unique_property_registration = models.Constraint(
            'UNIQUE(x_property_registration_id)',
            'El campo de identificación de la propiedad debe ser único!'
        )
    except AttributeError:
        # Odoo 18: Sintaxis antigua con _sql_constraints
        _sql_constraints = [
            ('unique_property_registration',
            'UNIQUE(x_property_registration_id)',
            'El campo de identificación de la propiedad debe ser único!')
        ]

    x_area_m2 = fields.Float(string='Area (m²)', help="Area total en metros cuadrados", default=0.0)
    x_bedrooms = fields.Integer(string='Habitaciones', help="Número de habitaciones de la propiedad", default=0)
    x_bathrooms = fields.Integer(string='Baños', help="Número de baños de la propiedad", default=0)
    x_parking_spaces = fields.Integer(string='Parqueaderos', help="Número de parqueaderos disponibles", default=0)
    cuarto_util = fields.Integer(string='Cuarto útil', help="Número de Cuartos útiles disponibles", default=0)
    terraza = fields.Integer(string='Terraza', help="Número de Terrazas disponibles", default=0)
    jardin = fields.Integer(string='Jardín', help="Número de zonas verdes disponibles", default=0)
    pisos = fields.Integer(string='Pisos', help="Número de Pisos disponibles", default=0)
    estrato = fields.Integer(string='Estrato', help="Estrato del inmueble", default=0)
    radicado_epm = fields.Integer(string='Radicado epm', help="Número de radicado de epm", default=0)
    tipo_inmueble = fields.Selection(const.TIPO_PROPIEDAD, string="Tipo de inmueble", default='Apartment')
    # varaibles contables
    canon = fields.Integer(string='Canon arrendamiento', help="canon de arrendamiento", default=0)
    monto_administracion = fields.Integer(string='Monto administración', help="Cobro de administración del inmueble", default=0)
    uso_destino = fields.Selection(
        selection=[
            ("residential", "Residencial"),
            ("commercial",  "Comercial"),
        ],
        string="Uso del inmueble",
        default="residential",
        required=True,
        tracking=True,
    )
    # uso_comercial = fields.Boolean(string='Uso comercial', help="Indica si el inmueble es para uso comercial", default=False)

    # Items de inventario en esta propiedad
    property_item_ids = fields.One2many('property.item', 'property_id', string='Inventario de la Propiedad')
    total_items_count = fields.Integer('Total Items', compute='_compute_items_count', store=True)
    total_inventory_value = fields.Monetary('Valor Total Inventario', compute='_compute_inventory_value', store=True)
    
    history_ids = fields.One2many(
        comodel_name='property.item.history',
        inverse_name='property_id',
        string='Historial de inventario'
    )
    
    x_property_building_id = fields.Many2one('x_buildings', string='Edificio') # Relación con el modelo x_buildings
    x_camera_placeholder = fields.Binary(
        string='Camera cámara de Entrega',
        attachment=True,
    )
    x_camera_recepcion = fields.Binary(
        string='Abrir Cámera de Recepción',
        attachment=True,
    )    
    x_camera_preview = fields.Binary(string='Camera Preview', attachment=True, help="Preview image from camera widget")
    x_camera_preview_entrada = fields.Binary(
        string='Vista previa Entrega', 
        attachment=True, 
        help="Vista previa de imagen/video para entrega"
    )
    x_camera_preview_recepcion = fields.Binary(
        string='Vista previa Recepción', 
        attachment=True, 
        help="Vista previa de imagen/video para recepción"
    )
    x_video_entrega_attachment_id = fields.Many2one(
        'ir.attachment', string='Video de Entrega', ondelete='set null'
    )

    x_video_recepcion_attachment_id = fields.Many2one(
        'ir.attachment', string='Video de Recepción', ondelete='set null'
        
        
    )
    #plantilla direccion en nueva propiedad    
    x_tipo_via = fields.Selection(const.TIPO, string="Tipo de vía principal")
    x_tipo_via_2 = fields.Selection(const.TIPO, string="Tipo de vía secundaria")

    x_nombre_via = fields.Char(string='Vía principal')
    x_numero_principal = fields.Char(string='Vía secundaria')
    x_numero_secundario = fields.Char(string='Número del lugar')
    x_complemento = fields.Char(string='Complemento')
    
    x_property_address = fields.Char(
        string='Dirección generada',
        compute='_compute_property_address',
        store=False,
    )
    x_property_geolocation = fields.Char(string="Direccion para geolocalizar", store=True)
    x_property_meter_reading_ids = fields.One2many(
        'x.meter.reading', 'x_account_analytic_account_id', string='Meter Readings'
    )
    owner_line_ids = fields.One2many(
        'account.analytic.account.owner.line',
        'analytic_account_id',
        string="Todos los propietarios"
    )
    beneficiary_line_ids = fields.One2many(
        'account.analytic.account.owner.line',
        'analytic_account_id',
        string="Beneficiarios",
        domain=[('is_main_payee', '=', True)]
    )
    non_beneficiary_line_ids = fields.One2many(
        'account.analytic.account.owner.line',
        'analytic_account_id',
        string="Propietarios",
        domain=[('is_main_payee', '=', False)]
    )
    subscription_count = fields.Integer(
        string="Rental Contracts",
        compute='_compute_contract_counts',
        store=False,
    )
    
    owner_contract_count = fields.Integer(
        string="Owner Contracts",
        compute='_compute_contract_counts',
        store=False,
    )
    owner_partner_ids = fields.Many2many(
        'res.partner', string='Propietarios (partners)',
        compute='_compute_owner_partners', store=False
    )    
    
    x_country_id = fields.Many2one(
        'res.country', string="País", required=False,
        default=lambda self: self.env.ref('base.co'))  # Por ejemplo, Colombia
    x_state_id = fields.Many2one(
        'res.country.state', string="Departamento / Estado", required=False)
    x_city_id = fields.Many2one(
        'res.city', string="Ciudad", required=False)
    
    sector = fields.Char(string="Barrio / Sector", required=False)
    
    default_plan_id = fields.Many2one(
        'account.analytic.plan',
        string='Plan Analítico',
        default=lambda self: self.env.ref(
            'industry_real_estate.analytic_plan_properties',
            raise_if_not_found=False
        ) and self.env.ref('industry_real_estate.analytic_plan_properties').id or False
    )
    
    owner_total_percent = fields.Float(compute='_compute_owner_totals', digits=(5,2))
    owner_remaining_percent = fields.Float(compute='_compute_owner_totals', digits=(5,2))
    
    x_is_property = fields.Boolean(
        string="Is Property",
        compute='_compute_x_is_property',
        store=True,
        readonly=True,
        default=True,
    )
    x_property_type = fields.Selection(const.TIPO_PROPIEDAD, string="Tipo de propiedad")    
    x_is_available = fields.Boolean(string="Propiedad disponible", default=True)  
    
    def get_formview_id(self, access_uid=None):
        """Forzar la vista de Propiedad cuando:
           - Viene desde nuestro campo (context['from_property_field']=True), o
           - El registro está marcado como propiedad (x_is_property=True).
           Fallback a la resolución estándar para otros casos.
        """
        self.ensure_one()
        # 1) Si viene desde nuestro enlace/campo, respeta SIEMPRE la vista de propiedad
        if self.env.context.get('from_property_field'):
            view = self.env.ref('industry_real_estate.property_form_view', raise_if_not_found=False)
            if view:
                return view.id

        # 2) Si este AAA es una propiedad, también forzamos nuestra vista
        if getattr(self, 'x_is_property', False):
            view = self.env.ref('industry_real_estate.property_form_view', raise_if_not_found=False)
            if view:
                return view.id

        # 3) Fallback estándar
        return super().get_formview_id(access_uid=access_uid)
    
    @api.onchange('x_property_address')
    def _onchange_x_property_address(self):
        if self.x_property_address and not self.name:
            self.name = self.x_property_address.split(',')[0].strip()
    
    @api.depends('plan_id')
    def _compute_x_is_property(self):
        # Si el registro no existe, evita excepción:
        plan = self.env.ref(
            'industry_real_estate.analytic_plan_properties',
            raise_if_not_found=False
        )
        for rec in self:
            if not rec.exists():
                continue
            rec.x_is_property = bool(plan and rec.plan_id == plan)
    
    @api.depends('owner_line_ids', 'owner_line_ids.owner_id')
    def _compute_owner_partners(self):
        for acc in self:
            if not acc.exists():
                continue
            acc.owner_partner_ids = [(6, 0, acc.owner_line_ids.exists().mapped('owner_id').ids or [])]

    def action_open_rental_contracts(self):
        """Abre los contratos (sale.order) de esta propiedad."""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'industry_real_estate.action_rental_contracts'
        )
        # filtra por la propiedad actual y pre-carga el default
        action['domain'] = [('x_account_analytic_account_id', '=', self.id)]
        action.setdefault('context', {})
        action['context'].update({'default_x_account_analytic_account_id': self.id})
        return action

    @api.depends('property_item_ids.product_id')
    def _compute_x_product(self):
        for rec in self:
            if not rec.exists():
                continue
            rec.x_product_tmpl_id = rec.property_item_ids[:1].product_id if rec.property_item_ids else False

    @api.depends('x_latitude', 'x_longitude')
    def _compute_dummy_map(self):
        for rec in self:
            if not rec.exists():
                continue
            if rec.x_latitude and rec.x_longitude:
                rec.x_dummy_map = rec._build_map_iframe(
                    rec.x_latitude, rec.x_longitude, w=500, h=200, zoom=16
                )
            else:
                # Sin coords => placeholder (o vacío si prefieres)
                rec.x_dummy_map = """
                    <div style="padding:8px;border:1px dashed #bbb;border-radius:6px;">
                        <em>Sin coordenadas. Usa “Geolocalizar”.</em>
                    </div>
                """

    @api.depends('property_item_ids.quantity')
    def _compute_items_count(self):
        for record in self:
            if not record.exists():
                continue
            record.total_items_count = sum(record.property_item_ids.mapped('quantity'))

    @api.depends('property_item_ids.value', 'property_item_ids.quantity')
    def _compute_inventory_value(self):
        for record in self:
            if not record.exists():
                continue
            record.total_inventory_value = sum(
                item.value * item.quantity for item in record.property_item_ids
            )


    @api.depends(
    'x_tipo_via', 'x_nombre_via', 'x_numero_principal',
    'x_numero_secundario', 'x_complemento',
    'x_cons_inm'  # <- ¡importante para que se recalcule al cambiar el consecutivo!
    )
    def _compute_property_address(self):
        for record in self:
            if not record.exists():
                continue
            partes = []
            parts = []

            tipo_via_dict = dict(record._fields['x_tipo_via'].selection)
            tipo_via = tipo_via_dict.get(record.x_tipo_via, '')

            if tipo_via and record.x_nombre_via:
                partes.append(f"{tipo_via} {record.x_nombre_via} #")
                parts.append(f"{tipo_via} {record.x_nombre_via}")

            if record.x_numero_principal:
                partes.append(f"{record.x_numero_principal} -")
                parts.append(f"{record.x_numero_principal}")

            if record.x_numero_secundario:
                partes.append(f"{record.x_numero_secundario}")

            if record.x_complemento:
                partes.append(f"{record.x_complemento},")
            
            if getattr(record, 'sector', False):
                partes.append(f"{record.sector},")
                parts.append(record.sector)

            if record.x_city_id:
                partes.append(f"{record.x_city_id.name},")
                parts.append(record.x_city_id.name)

            if record.x_state_id:
                partes.append(f"{record.x_state_id.name},")
                parts.append(record.x_state_id.name)

            if record.x_country_id:
                partes.append(f"{record.x_country_id.name}")
                parts.append(record.x_country_id.name)

            # Normaliza espacios y comas
            addr_pretty = " ".join(partes).replace(" ,", ",").strip()
            geo_pretty  = " ".join(parts).strip()

            record.x_property_address     = addr_pretty
            record.x_property_geolocation = geo_pretty

            # Prefijo con el consecutivo si existe
            cons = (record.x_cons_inm or '').strip()
            first = addr_pretty.split(',')[0].strip() if addr_pretty else ''
            record.name = f"{cons} - {first}" if cons else first


    def post_video_message(self, field_name):
        self.ensure_one()
        attachment = self[field_name]
        if attachment:
            self.message_post(
                body=f"Video adjunto: {attachment.name}",
                attachment_ids=[attachment.id],
            )

    def print_contract(self):
        print("examples")
        # return self.env.ref('industry_real_estate.action_report_contract').report_action(self)


    # [ (tipo de comando, id de la propiedad, modelo ) ]
    def _split_o2m_cmd(self, cmd):
        """Devuelve (ctype, rec_id, data) tolerando longitudes 1/2/3."""
        if not isinstance(cmd, (list, tuple)):
            return None, None, None
        ln = len(cmd)
        if ln == 3: return cmd[0], cmd[1], cmd[2]
        if ln == 2: return cmd[0], cmd[1], False
        if ln == 1: return cmd[0], False, False
        return None, None, None

    @api.model
    def _parse_owner_line_commands(self, commands):
        res = {'create': [], 'update': [], 'delete': [], 'clear': False, 'replace': []}
        for cmd in commands or []:
            ctype, rec_id, data = self._split_o2m_cmd(cmd)
            if ctype == 0:
                res['create'].append(data or {})
            elif ctype == 1:
                res['update'].append((rec_id, data or {}))
            elif ctype == 2:
                res['delete'].append(rec_id)
            elif ctype == 5:
                res['clear'] = True
            elif ctype == 6:
                res['replace'] = data or []
        return res
    
    def _prepare_owner_change_messages(self, before_lines, commands, before_snapshot=None):
        parsed = self._parse_owner_line_commands(commands)
        before_snapshot = before_snapshot or {}
        before_map = {l.id: l for l in before_lines}
        msgs = []

        # --- Borrados: usar snapshot (NO read/NO browse) ---
        if parsed['delete']:
            for rec_id in parsed['delete']:
                snap = before_snapshot.get(rec_id, {})
                owner_name = snap.get('owner_name') or snap.get('name') or '-'
                pct = snap.get('participation_percent') or snap.get('beneficial_porcentage') or 0.0
                msgs.append(_("Eliminado propietario/beneficiario: %(name)s (%%: %(pct)s)") % {
                    'name': owner_name, 'pct': pct
                })

        # Actualizaciones
        interesting = ['participation_percent', 'beneficial_porcentage', 'iva', 'is_main_payee']
        for rec_id, upd in parsed['update']:
            old = before_map.get(rec_id)
            if not old:
                continue
            diffs = []
            for f in interesting:
                if f in upd and (getattr(old, f) or False) != (upd.get(f) or False):
                    diffs.append(f"{f}: {getattr(old, f) or 0} → {upd.get(f)}")
            if diffs:
                name = (old.owner_id.display_name or getattr(old, 'name', False) or str(rec_id))
                msgs.append(_("Actualizado %(name)s → ") % {'name': name} + "; ".join(diffs))

        # Altas
        for data in parsed['create']:
            owner = ''
            if data.get('owner_id'):
                owner = self.env['res.partner'].browse(data['owner_id']).display_name
            name = owner or data.get('name') or '-'
            pct = data.get('participation_percent') or data.get('beneficial_porcentage') or 0.0
            msgs.append(_("Agregado propietario/beneficiario: %(name)s (%%: %(pct)s)") % {'name': name, 'pct': pct})

        if parsed['clear']:
            msgs.append(_("Se han eliminado todas las líneas de propietarios/beneficiarios."))
        if parsed['replace']:
            msgs.append(_("Reemplazo completo de líneas (ids: %s).") % parsed['replace'])

        return msgs

    def write(self, vals):
        results = True
        for record in self:
            before_owner_lines = record.owner_line_ids.exists()
            before_snapshot = {
                l.id: {
                    'owner_name': l.owner_id.display_name,
                    'name': l.name,  # legacy
                    'participation_percent': l.participation_percent or 0.0,
                    'beneficial_porcentage': getattr(l, 'beneficial_porcentage', 0.0) or 0.0,
                }
                for l in before_owner_lines
            }
            res = super(AccountAnalyticAccount, record).write(vals)

            # Prepara mensajes (sin hacer message_post todavía)
            msgs = []
            # Si cambian propietarios “no beneficiarios”
            if 'non_beneficiary_line_ids' in vals:
                msgs += record._prepare_owner_change_messages(before_owner_lines, vals['non_beneficiary_line_ids'], before_snapshot)
            # Si cambian TODAS las líneas (por si tu vista usa owner_line_ids)
            if 'owner_line_ids' in vals:
                msgs += record._prepare_owner_change_messages(before_owner_lines, vals['owner_line_ids'], before_snapshot)

            # Asegura plan por defecto si aplica
            if record.x_is_property and not record.plan_id:
                plan = self.env.ref('industry_real_estate.analytic_plan_properties', raise_if_not_found=False)
                if plan:
                    record.plan_id = plan.id

            # Escribe realmente (aquí se borran líneas)
            results = results and res

            # Ahora sí publica mensajes (ya NO hay recordsets de owner_line en uso)
            if msgs:
                record.message_post(body="\n".join(msgs))

        return results
    
    def _geocode_address(self, address):
        """Geocodifica con Nominatim (OSM) sin costo."""
        if not address:
            return None, None
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": address, "format": "json", "limit": 1}
        headers = {"User-Agent": "realnet-odoo/1.0 (ingenieria@realnet.com.co)"}
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data:
            return None, None
        return float(data[0]["lat"]), float(data[0]["lon"])
    
    def _mercator_px(self, lat, lon, z):
        n = 2.0 ** z
        x = (lon + 180.0) / 360.0 * n * 256.0
        lat_rad = math.radians(lat)
        y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n * 256.0
        return x, y

    def _px_to_lonlat(self, x, y, z):
        n = 2.0 ** z
        lon = x / (n * 256.0) * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / (n * 256.0))))
        lat = math.degrees(lat_rad)
        return lat, lon

    def _build_map_iframe(self, lat, lon, w=720, h=260, zoom=14):
        # 1) bbox exacto para el viewport (w x h) centrado en (lat,lon)
        x_c, y_c = self._mercator_px(lat, lon, zoom)
        dx, dy = w / 2.0, h / 2.0
        x_min, y_max = x_c - dx, y_c + dy
        x_max, y_min = x_c + dx, y_c - dy
        min_lat, min_lon = self._px_to_lonlat(x_min, y_max, zoom)
        max_lat, max_lon = self._px_to_lonlat(x_max, y_min, zoom)

        src = (
            "https://www.openstreetmap.org/export/embed.html"
            f"?bbox={min_lon},{min_lat},{max_lon},{max_lat}&layer=mapnik"
        )

        # 2) MUY IMPORTANTE: usar el MISMO tamaño fijo en el contenedor
        return (
            f'<div style="width:{w}px;height:{h}px;overflow:hidden;'
            f'border:1px solid #000;border-radius:6px;">'
            f'<iframe src="{src}" loading="lazy" referrerpolicy="no-referrer-when-downgrade" '
            f'style="width:{w}px;height:{h}px;border:0;display:block;"></iframe>'
            f'</div>'
        )
    
    @api.model_create_multi
    def create(self, vals_list):
        plan_id = self.env.ref('industry_real_estate.analytic_plan_properties').id
        for vals in vals_list:
            # 1) Garantiza NAME siempre (obligatorio)
            if not vals.get('name'):
                # 1.a) si hay dirección compuesta, toma la primera parte
                name = None
                addr = vals.get('x_property_address')
                if addr:
                    name = addr.split(',', 1)[0].strip()

                # 1.b) si no hay dirección, arma con campos unitarios
                if not name:
                    parts = [
                        vals.get('x_tipo_via'),
                        vals.get('x_nombre_via'),
                        vals.get('x_numero_principal'),
                        vals.get('x_numero_secundario'),
                        vals.get('x_complemento'),
                    ]
                    parts = [str(p).strip() for p in parts if p]
                    if parts:
                        name = " ".join(parts)

                # 1.c) fallback final para cumplir NOT NULL
                if not name:
                    name = _("Propiedad sin nombre")

                vals['name'] = name
            if vals.get('x_is_property') and not vals.get('default_plan_id'):
                vals['default_plan_id'] = plan_id
            if 'non_beneficiary_line_ids' in vals:
                # No hay record aún; simulación contra conjunto vacío
                snap = self._apply_o2m_commands(self.env['account.analytic.account.owner.line'].browse(), vals.get('non_beneficiary_line_ids'))
                # Para el mensaje de beneficiarios, no habrá nombres; es suficiente validar totales
                self._validate_snapshot_or_raise(snap, display_parent=self)
            
        return super().create(vals_list)
    
    def _geocode_address_osm(self, address):
        """Geocodifica una dirección usando OpenStreetMap Nominatim"""
        if not address:
            return None, None
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": address,
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
        }
        try:
            response = requests.get(url, params=params, headers={"User-Agent": "Realnet/1.0"})
            response.raise_for_status()
            data = response.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
        except Exception:
            return None, None
        return None, None

    def _jitter_point(self, lat, lon, radius_m=0):
        if not radius_m:
            return lat, lon
        radius_deg = radius_m / 111000.0
        delta_lat = random.uniform(-radius_deg, radius_deg)
        delta_lon = random.uniform(-radius_deg, radius_deg)
        return lat + delta_lat, lon + delta_lon

    def action_geolocalizar(self):
        for rec in self:
            lat, lon = rec._geocode_address_osm(rec.x_property_geolocation)
            if lat is None:
                raise UserError("No fue posible geolocalizar la dirección...")
            lat_jit, lon_jit = rec._jitter_point(lat, lon, radius_m=500) # modificador de ubicación exacta a ubicación apróximada
            rec.write({'x_latitude': lat_jit, 'x_longitude': lon_jit})
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_create_invoice_meters(self):
        self.ensure_one()
        meter_readings = self.x_property_meter_reading_ids.filtered(
            lambda l: not l.x_invoice_id and (l.x_usage or 0) > 0
        )
        if not meter_readings:
            raise UserError(_("No hay lecturas para facturar."))

        partner = self.x_rental_contract_id.partner_id
        if not partner:
            raise UserError(_("La propiedad no tiene un cliente asociado."))

        lines = []
        for r in meter_readings:
            name = f"{r.x_date} - {r.x_description}" if r.x_description else str(r.x_date)
            lv = {
                'name': name,
                'price_unit': r.x_meter_id.x_price or 0.0,
                'quantity': r.x_usage or 0.0,
                # En v16+ las llaves de analytic_distribution deben ser str
                'analytic_distribution': {str(self.id): 100},
            }
            # Sugerencia: usa un producto para que no falte cuenta de ingreso/impuestos
            if getattr(r.x_meter_id, 'product_id', False):
                lv['product_id'] = r.x_meter_id.product_id.id
            else:
                # fallback a cuenta de ingresos (si tienes un campo configurado)
                income_account = getattr(r.x_meter_id, 'property_account_income_id', False) or \
                                getattr(getattr(r.x_meter_id, 'categ_id', False), 'property_account_income_categ_id', False)
                if income_account:
                    lv['account_id'] = income_account.id

            lines.append((0, 0, lv))

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_origin': self.name,
            'invoice_line_ids': lines,
        })

        # ¡OJO! No hacer meter_readings['x_invoice_id'] = invoice.id
        meter_readings.write({'x_invoice_id': invoice.id})

        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = invoice.id
        return action

    """ SECCION DE PROPIETARIOS """
    def _contract_context_for_owner(self, prop, owner_line):
        return {
            "NOMBRE_PROPIETARIO": owner_line.owner_id.display_name,
            "DOCUMENTO_PROPIETARIO": owner_line.owner_id.vat or "",
            "DIRECCION_INMUEBLE": prop.x_property_address or prop.name,
            "PORCENTAJE_PROPIETARIO": f"{owner_line.participation_percent:.2f}%",
            "FECHA_INICIO_CONTRATO": fields.Date.today().strftime('%Y-%m-%d'),
            "FECHA_FIN_CONTRATO": "",
            "LISTA_PROPIETARIOS": ", ".join(
                f"{l.owner_id.display_name} ({l.participation_percent:.0f}%)"
                for l in prop.owner_line_ids.exists()
            ),
        }

    def action_open_owner_contracts(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('industry_real_estate.action_owner_contracts')
        action['domain'] = [
            ('x_account_analytic_account_id','=', self.id),
            ('ecoerp_contract','=', True),
            ('ecoerp_scope','=','owner'),
        ]
        ctx = dict(action.get('context') or {})
        ctx.update({
            'default_ecoerp_contract': True,
            'default_ecoerp_scope': 'owner',
            'default_x_account_analytic_account_id': self.id,
        })
        action['context'] = ctx
        return action

    def _compute_contract_counts(self):
        Order = self.env['sale.order'].exists()

        # COMPATIBILIDAD ODOO 18/19:
        # En Odoo 19, read_group está deprecado, usar _read_group
        # En Odoo 18, _read_group no existe, usar read_group
        domain = [('ecoerp_contract', '=', True),
                  ('x_account_analytic_account_id', 'in', self.ids)]
        groupby = ['x_account_analytic_account_id', 'ecoerp_scope']

        try:
            # Odoo 19: usar _read_group
            # _read_group desempaqueta directamente: groupby_values + aggregate_values
            # Para 2 groupby + 1 aggregate: (groupby1, groupby2, aggregate1)
            grouped = []
            for aa_record, scope, count in Order._read_group(
                domain=domain,
                groupby=groupby,
                aggregates=['__count'],
            ):
                if aa_record:
                    grouped.append({
                        'x_account_analytic_account_id': (aa_record.id, aa_record.name),
                        'ecoerp_scope': scope,
                        '__count': count,
                    })
        except AttributeError:
            # Odoo 18: usar read_group (método antiguo)
            grouped = Order.read_group(
                domain=domain,
                fields=['__count'],
                groupby=groupby,
            )

        # base en cero
        counts = {rid: {'rental': 0, 'owner': 0} for rid in self.ids}
        for g in grouped:
            aa_id = g['x_account_analytic_account_id'][0]
            scope = g.get('ecoerp_scope')
            if scope in ('rental', 'owner'):
                counts[aa_id][scope] = g['__count']

        for rec in self:
            if not rec.exists():
                continue
            rec.subscription_count   = counts.get(rec.id, {}).get('rental', 0)
            rec.owner_contract_count = counts.get(rec.id, {}).get('owner', 0)
            
    # Validación en guardado del padre y beneficiarios
    @api.depends('owner_line_ids.participation_percent')
    def _compute_owner_totals(self):
        for acc in self:
            if not acc.exists():
                continue
            total = round(sum((l.participation_percent or 0.0) for l in acc.owner_line_ids.exists()), 2)
            acc.owner_total_percent = total
            acc.owner_remaining_percent = max(0.0, round(100.0 - total, 2))
            
    @classmethod
    def _pct_round(cls, v):
        return float_round(v or 0.0, precision_digits=const.PCT_DIGITS)
    @classmethod
    def _pct_sum(cls, vals):
        # Suma con redondeo por línea y del total para evitar arrastres binarios
        return float_round(sum(cls._pct_round(x) for x in vals), precision_digits=const.PCT_DIGITS)
    
    def _apply_o2m_commands(self, current_recs, commands):
        """
        Devuelve una lista "virtual" de dicts con el estado resultante de owner_line_ids,
        aplicando los comandos O2M de vals['owner_line_ids'] sin escribir en BD.
        """
        # snapshot inicial de lo actual
        snap = [{
            'id': l.id,
            'is_main_payee': bool(l.is_main_payee),
            'participation_percent': l.participation_percent or 0.0,
            'beneficial_porcentage': l.beneficial_porcentage or 0.0,
            'parent_owner_line_id': l.parent_owner_line_id.id if l.parent_owner_line_id else False,
        } for l in current_recs]

        # index por id para cambios rápidos
        by_id = {x['id']: x for x in snap if x['id']}

        def add_line(d):
            snap.append({
                'id': False,
                'is_main_payee': bool(d.get('is_main_payee')),
                'participation_percent': d.get('participation_percent') or 0.0,
                'beneficial_porcentage': d.get('beneficial_porcentage') or 0.0,
                'parent_owner_line_id': d.get('parent_owner_line_id') or False,
            })

        if not commands:
            return snap

        for cmd in commands:
            op = cmd[0]
            if op == 0:
                # (0,0,vals) create
                add_line(cmd[2] or {})
            elif op == 1:
                # (1,id,vals) write
                rec_id = cmd[1]
                vals = cmd[2] or {}
                if rec_id in by_id:
                    rec = by_id[rec_id]
                    for k in ('is_main_payee','participation_percent','beneficial_porcentage','parent_owner_line_id'):
                        if k in vals:
                            rec[k] = vals[k] or (0.0 if k in ('participation_percent','beneficial_porcentage') else False)
            elif op == 2:
                # (2,id) delete
                rec_id = cmd[1]
                snap[:] = [x for x in snap if x['id'] != rec_id]
                by_id.pop(rec_id, None)
            elif op == 4:
                # (4,id) link (no suele aplicar aquí)
                pass
            elif op == 5:
                # (5,) unlink all
                snap.clear(); by_id.clear()
            elif op == 6:
                # (6,0,ids) replace with ids (sin cambios de campos)
                # Mantén sólo los que estén en ids
                ids = set(cmd[2] or [])
                snap[:] = [x for x in snap if x['id'] in ids]
                by_id = {x['id']: x for x in snap if x['id']}
            # otros opcodes no aplican aquí
        return snap

    def _validate_snapshot_or_raise(self, snap, display_parent):
        """
        Valida sobre la 'foto' (snap) resultante:
        - Propietarios (is_main_payee=False): suma ≤ 100
        - Beneficiarios por propietario padre: suma ≤ 100
        """
        # --- Propietarios ---
        owner_vals = [self._pct_round(x['participation_percent']) for x in snap if not x['is_main_payee']]
        owners_total = self._pct_sum(owner_vals)
        if float_compare(owners_total, 100.0, precision_digits=const.PCT_DIGITS) == 1:
            raise ValidationError(_("Registro de propiedad.\nLa suma de porcentajes de propietarios no puede exceder 100%% (actual: %.2f%%).") % owners_total)

        # --- Beneficiarios por propietario padre ---
        buckets = defaultdict(list)
        for x in snap:
            if x['is_main_payee'] and x['parent_owner_line_id']:
                buckets[x['parent_owner_line_id']].append(self._pct_round(x['beneficial_porcentage']))
        for parent_id, vals in buckets.items():
            total = self._pct_sum(vals)
            if float_compare(total, 100.0, precision_digits=const.PCT_DIGITS) == 1:
                # Resuelve nombre legible si está en el cache
                parent_name = _("(propietario)")
                try:
                    parent_rec = display_parent.owner_line_ids.exists().filtered(lambda l: l.id == parent_id)
                    if parent_rec:
                        parent_name = parent_rec.owner_id.display_name or parent_name
                except Exception:
                    pass
                raise ValidationError(
                    _("Registro de propiedad.\nLa suma de porcentajes de beneficiarios para el propietario %s no puede exceder 100%% (actual: %.2f%%).")
                    % (parent_name, total)

                )
                
    @api.constrains('x_cons_inm', 'x_is_property')
    def _check_cons_inm_unique(self):
        """Unicidad lógica: sólo aplica a propiedades y sólo si viene informado."""
        for rec in self:
            if rec.x_is_property and rec.x_cons_inm:
                dup = self.search_count([
                    ('id', '!=', rec.id),
                    ('x_is_property', '=', True),
                    ('x_cons_inm', '=', rec.x_cons_inm),
                ])
                if dup:
                    raise ValidationError(
                        _("Ya existe otra propiedad con el consecutivo %s.") % rec.x_cons_inm
                    )
                    
    def _normalize_pct(p):
        # Normaliza 0..100 → 0..1 sin redondear
        try:
            return max(0.0, float(p)) / 100.0
        except Exception:
            return 0.0
                    
    def _get_property_owners_with_shares(self, *, strict=True, precision=2, include_beneficiaries=True):
        """
        Devuelve [(partner, share_0_a_1), ...] para ESTA propiedad.

        Reglas:
        - Propietario raíz: % global (0..1).
        - Beneficiarios del propietario: % relativo al propietario (0..1 del padre).
        - Si beneficiarios < 100%, remanente al propietario.
        """
        self.ensure_one()

        owners = self.non_beneficiary_line_ids.exists()
        benefs = self.beneficiary_line_ids.exists()

        if not owners:
            if strict:
                raise ValidationError(_("La propiedad '%s' no tiene líneas de propietarios/beneficiarios.") % self.display_name)
            return []

        # Propietarios raíz (sin padre)
        root_owner_lines = owners.filtered(lambda l: not l.parent_owner_line_id)
        if not root_owner_lines and strict:
            raise ValidationError(_("No se encontraron líneas raíz de propietarios en '%s'.") % self.display_name)

        # Helpers
        def _owner_base_share(line):
            # Preferir real_participation_percent si existe; si no, participation_percent
            pct = getattr(line, 'participation_percent', 0.0) or 0.0
            return max(0.0, float(pct)) / 100.0  # 0..1

        def _benef_rel_share(benef_line):
            # % relativo al propietario (NO global)
            pct = getattr(benef_line, 'participation_percent', 0.0) or 0.0
            return max(0.0, float(pct)) / 100.0  # 0..1

        bucket = {}  # partner -> share(0..1) acumulado sin redondeo

        # Si no vamos a considerar beneficiarios o no existen, atajo SOLO propietarios
        consider_benefs = include_beneficiaries and bool(benefs)
        if not consider_benefs:
            for root in root_owner_lines:
                partner = root.owner_id
                if not partner:
                    continue
                base_share = _owner_base_share(root)
                if base_share > 0.0:
                    bucket[partner] = bucket.get(partner, 0.0) + base_share
            # Validación y salida
            total = sum(bucket.values())
            if strict and float_compare(total, 1.0, precision_digits=4) != 0:
                raise UserError(
                    _("La suma de participaciones de la propiedad '%(prop)s' debe ser 100%% (actual: %(tot)s%%).")
                    % {'prop': self.display_name, 'tot': float_round(total * 100.0, precision_digits=precision)}
                )
            items = sorted(bucket.items(), key=lambda kv: kv[0].id)
            return items

        # Caso con beneficiarios
        for root in root_owner_lines:
            owner_partner = root.owner_id
            if not owner_partner:
                continue

            base_share = _owner_base_share(root)
            if base_share <= 0.0:
                continue

            # Beneficiarios SOLO del propietario actual
            root_benefs = benefs.filtered(lambda l: l.parent_owner_line_id and l.parent_owner_line_id.id == root.id)

            if not root_benefs:
                # Sin beneficiarios: todo para el propietario
                bucket[owner_partner] = bucket.get(owner_partner, 0.0) + base_share
                continue

            # Suma relativa de beneficiarios (0..1 del propietario)
            rel_sum = sum(_benef_rel_share(b) for b in root_benefs)

            # Si excede 100%, error
            if float_compare(rel_sum, 1.0, precision_digits=precision) == 1:
                raise UserError(_(
                    "La suma de beneficiarios del propietario '%(owner)s' excede 100%% "
                    "(actual: %(val)s%%) en la propiedad '%(prop)s'."
                ) % {
                    'owner': owner_partner.display_name,
                    'prop' : self.display_name,
                    'val'  : float_round(rel_sum * 100.0, precision_digits=precision),
                })

            # Asignación global a cada beneficiario = base_share * rel_pct
            for b in root_benefs:
                bp = b.owner_id
                if not bp:
                    continue
                rel = _benef_rel_share(b)
                if rel <= 0.0:
                    continue
                alloc = base_share * rel
                if alloc > 0.0:
                    bucket[bp] = bucket.get(bp, 0.0) + alloc

            # Remanente al propietario si beneficiarios no llegan a 100%
            if float_compare(rel_sum, 1.0, precision_digits=precision) == -1:
                remainder = base_share * (1.0 - rel_sum)
                if remainder > 0.0:
                    bucket[owner_partner] = bucket.get(owner_partner, 0.0) + remainder

        # Validación final ≈ 100%
        total = sum(bucket.values())
        if strict and float_compare(total, 1.0, precision_digits=4) != 0:
            raise UserError(
                _("La suma de participaciones de la propiedad '%(prop)s' debe ser 100%% (actual: %(tot)s%%).")
                % {'prop': self.display_name, 'tot': float_round(total * 100.0, precision_digits=precision)}
            )

        items = sorted(bucket.items(), key=lambda kv: kv[0].id)
        return items
    
    @api.model
    def _cron_auto_assign_property_owner(self, limit=500):
        """
        ECOERP: Asigna automáticamente un propietario con 100% de participación
        a las propiedades que no tengan ninguno.
        """
        from random import SystemRandom
        rnd = SystemRandom()
        partner_m = self.env['res.partner']
        line_m = self.env['account.analytic.account.owner.line']

        # 1) Buscar candidatos válidos (activos)
        candidate_domain = [('active', '=', True)]
        candidates = partner_m.search(candidate_domain)
        if not candidates:
            _logger.warning("ECOERP AutoOwner: No hay contactos candidatos para asignar como propietarios.")
            return True

        # 2) Traer propiedades activas (si existe x_is_property)
        prop_domain = [('active', '=', True)]
        if 'x_is_property' in self._fields:
            prop_domain.append(('x_is_property', '=', True))

        props = self.search(prop_domain, limit=limit)
        if not props:
            _logger.warning("ECOERP AutoOwner: No hay propiedades para revisar.")
            return True

        creadas, omitidas = 0, 0

        for prop in props:
            # Si ya tiene propietarios, se omite
            if getattr(prop, 'owner_line_ids', False) and prop.owner_line_ids.exists():
                omitidas += 1
                continue

            prop_company = getattr(prop, 'company_id', False)
            compatibles = candidates
            if prop_company:
                compatibles = candidates.filtered(
                    lambda p: not p.company_id or p.company_id == prop_company
                )

            pool = compatibles or candidates
            owner = rnd.choice(pool)

            vals = {
                'analytic_account_id': prop.id,
                'owner_id': owner.id,
                'participation_percent': 100.0,
                'real_participation_percent': 100.0,
                'is_main_payee': False,
            }
            line_m.create(vals)
            creadas += 1

            # Notifica en el chatter (opcional)
            try:
                prop.message_post(
                    body=_("Propietario asignado automáticamente: <b>%s</b> (100%%).") % owner.display_name
                )
            except Exception:
                _logger.warning("ECOERP AutoOwner: no se pudo postear mensaje en %s.", prop.display_name)

        _logger.info(
            "ECOERP AutoOwner: %s propietarios asignados, %s propiedades omitidas (ya tenían dueño).",
            creadas, omitidas
        )
        return True
