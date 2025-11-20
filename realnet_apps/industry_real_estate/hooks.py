from odoo import api, SUPERUSER_ID, tools
import logging

_logger = logging.getLogger(__name__)

_IDS = [
    'sale.action_quotations',
    'sale.action_orders',
    'sale.action_quotations_with_onboarding',
]

def post_init_all(env):
    # env = api.Environment(cr, SUPERUSER_ID, {})
    post_init_update_sale_actions(env)
    post_init_flag_partners(env)
    post_init_define_owners(env)
    post_init_set_analytic_plan(env)
    post_init_set_group_categories(env)
    post_init_set_product_categories(env)
    post_init_set_odoo_version_views(env)

def post_init_update_sale_actions(env):
    for xmlid in _IDS:
        act = env.ref(xmlid, raise_if_not_found=False)
        if not act or act._name != 'ir.actions.act_window':
            continue
        base_dom = []
        if xmlid.endswith('action_quotations') or xmlid.endswith('quotations_with_onboarding'):
            base_dom = [('state','in',('draft','sent'))]
        elif xmlid.endswith('action_orders'):
            base_dom = [('state','not in',('draft','sent','cancel'))]
        # fuerza excluir ECOERP en Ventas
        new_dom = base_dom + [('ecoerp_contract','!=', True)]
        act.write({'domain': repr(new_dom)})

def post_init_flag_partners(env):
    env['res.partner'].search([('customer_rank','>',0)]).write({'is_tenant': True})
    owners = env['account.analytic.account.owner.line'].mapped('owner_id')
    if owners:
        owners.write({'is_property_owner': True, 'supplier_rank': 1})

def post_init_define_owners(env):
    lines = env['account.analytic.account.owner.line'].search([('owner_id','=',False), ('name','!=',False)])
    for l in lines:
        if l.name.partner_id:
            l.owner_id = l.name.partner_id.id
    partners = lines.mapped('owner_id')
    if partners:
        partners.write({'is_property_owner': True, 'supplier_rank': 1})

def post_init_set_analytic_plan(env):
    # por xml
    plan = env.ref('industry_real_estate.analytic_plan_properties', raise_if_not_found=False)
    if not plan:# por cuentas analiticas
        plan = env['account.analytic.plan'].search([('name', 'ilike', 'Properties')], limit=1)
    if not plan: # la creamos
        plan = env['account.analytic.plan'].create({'name': 'Properties'})
    aaa = env['account.analytic.account']
    field_name = 'analytic_plan_id' if 'analytic_plan_id' in aaa._fields else (
        'default_plan_id' if 'default_plan_id' in aaa._fields else None
    )
    if not field_name:
        # Nada que asignar si el campo no existe
        return
    domain = [('x_is_property', '=', True), (field_name, '=', False)]
    aaa.sudo().search(domain).write({field_name: plan.id})


def post_init_set_group_categories(env):
    """
    Compatibilidad Odoo 18/19: Asigna category_id (v18) o application_id (v19)
    a los grupos de seguridad, y asigna grupos al usuario admin.

    Cambios en Odoo 19:
    - res.groups: 'category_id' → 'application_id'
    - res.users: 'groups_id' → 'group_ids'
    """
    # 1. Obtener la categoría oculta
    hidden_category = env.ref('base.module_category_hidden', raise_if_not_found=False)
    if not hidden_category:
        return

    # 2. Grupos a configurar
    group_xmlids = [
        'industry_real_estate.group_real_estate_user',
        'industry_real_estate.group_property_manager',
    ]

    groups_to_assign = []

    for xmlid in group_xmlids:
        group = env.ref(xmlid, raise_if_not_found=False)
        if not group:
            continue

        # Asignar categoría al grupo
        if 'application_id' in group._fields:
            # Odoo 19: usar application_id
            if not group.application_id:
                group.write({'application_id': hidden_category.id})
        elif 'category_id' in group._fields:
            # Odoo 18: usar category_id
            if not group.category_id:
                group.write({'category_id': hidden_category.id})

        # Agregar a la lista de grupos para asignar al admin
        groups_to_assign.append(group.id)

    # 3. Asignar grupos al usuario admin
    if groups_to_assign:
        admin_user = env.ref('base.user_admin', raise_if_not_found=False)
        if admin_user:
            # Detectar qué campo usar en res.users
            if 'group_ids' in admin_user._fields:
                # Odoo 19: usar group_ids
                admin_user.write({'group_ids': [(4, gid) for gid in groups_to_assign]})
            elif 'groups_id' in admin_user._fields:
                # Odoo 18: usar groups_id
                admin_user.write({'groups_id': [(4, gid) for gid in groups_to_assign]})


def post_init_set_product_categories(env):
    """
    Compatibilidad Odoo 18/19: Asigna categorías a productos.

    Cambios en Odoo 19:
    - product.product_category_all fue eliminado
    - Nuevas categorías: product_category_services, product_category_goods, product_category_expenses
    """
    # Detectar qué categoría existe según la versión de Odoo
    service_category = None

    # Intentar Odoo 19 primero
    service_category = env.ref('product.product_category_services', raise_if_not_found=False)

    # Si no existe, intentar Odoo 18
    if not service_category:
        service_category = env.ref('product.product_category_all', raise_if_not_found=False)

    # Si aún no existe, buscar por nombre o crear una
    if not service_category:
        service_category = env['product.category'].search([('name', '=', 'Services')], limit=1)
        if not service_category:
            service_category = env['product.category'].create({'name': 'Services'})

    if not service_category:
        return

    # Lista de XMLIDs de productos a actualizar
    product_xmlids = [
        'industry_real_estate.product_product_42',
        'industry_real_estate.product_product_43',
        'industry_real_estate.product_product_44',
        'industry_real_estate.product_product_45',
        'industry_real_estate.product_product_46',
        'industry_real_estate.product_product_47',
        'industry_real_estate.product_product_48',
        'industry_real_estate.product_product_49',
        'industry_real_estate.product_product_50',
    ]

    # Asignar categoría a cada producto
    for xmlid in product_xmlids:
        product = env.ref(xmlid, raise_if_not_found=False)
        if product and not product.categ_id:
            product.write({'categ_id': service_category.id})


def post_init_set_odoo_version_views(env):
    """
    Compatibilidad Odoo 18/19: Activa la vista correcta según la versión.

    Cambios en Odoo 19:
    - El page 'optional_products' fue eliminado completamente de sale_subscription
    - Vista base rental_form_view es siempre activa
    - Vista heredada rental_form_view_odoo18 se activa solo en Odoo 18 (oculta optional_products)
    - Vista heredada rental_form_view_odoo19 se activa solo en Odoo 19 (no hace nada)
    - CRM quick_create: estructura de label cambió (label vs div+icon)
    """
    # Detectar versión de Odoo mediante detección de características
    is_odoo18 = _detect_odoo_version(env)

    # Activar vistas según versión usando función genérica
    _activate_version_specific_views(
        env,
        is_odoo18,
        views_config=[
            # Vistas de rental_form
            {
                'xmlid_18': 'industry_real_estate.rental_form_view_odoo18',
                'xmlid_19': 'industry_real_estate.rental_form_view_odoo19',
            },
            # Vistas de CRM quick_create
            {
                'xmlid_18': 'industry_real_estate.view_crm_lead_form_quick_create_inherit_18',
                'xmlid_19': 'industry_real_estate.view_crm_lead_form_quick_create_inherit_19',
                'data_file_18': 'data/ir_ui_views_odoo18.xml',
                'data_file_19': 'data/ir_ui_views_odoo19.xml',
            },
        ]
    )

    # Cargar filtros específicos de versión
    _post_init_load_version_specific_filters(env, is_odoo18)


def _detect_odoo_version(env):
    """
    Detecta la versión de Odoo mediante características específicas.

    Returns:
        bool: True si es Odoo 18, False si es Odoo 19 o superior
    """
    # Intentar obtener la vista padre de sale_subscription
    parent_view = env.ref('sale_subscription.sale_subscription_order_view_form', raise_if_not_found=False)

    if not parent_view:
        # Fallback: detectar por otras características
        _logger.warning('No se pudo detectar versión por sale_subscription, usando fallback')
        # En Odoo 19, ir.filters.user_id cambió a user_ids (Many2many)
        filters_model = env['ir.filters']
        return 'user_id' in filters_model._fields

    # Detectar si el page optional_products existe en la vista padre
    return 'optional_products' in (parent_view.arch_db or '')


def _activate_version_specific_views(env, is_odoo18, views_config):
    """
    Activa vistas específicas de versión basándose en configuración.

    Args:
        env: Odoo environment
        is_odoo18: True si es Odoo 18, False si es Odoo 19
        views_config: Lista de diccionarios con configuración de vistas:
            - xmlid_18: XML ID de la vista para Odoo 18
            - xmlid_19: XML ID de la vista para Odoo 19
            - data_file_18 (opcional): Archivo XML a cargar para Odoo 18
            - data_file_19 (opcional): Archivo XML a cargar para Odoo 19

    Example:
        views_config=[
            {
                'xmlid_18': 'module.view_odoo18',
                'xmlid_19': 'module.view_odoo19',
                'data_file_18': 'data/views_odoo18.xml',  # opcional
                'data_file_19': 'data/views_odoo19.xml',  # opcional
            },
        ]
    """
    for config in views_config:
        # Cargar archivos XML si están especificados
        if is_odoo18 and config.get('data_file_18'):
            _load_data_file(env, config['data_file_18'])
        elif not is_odoo18 and config.get('data_file_19'):
            _load_data_file(env, config['data_file_19'])

        # Obtener referencias a las vistas
        view_odoo18 = env.ref(config['xmlid_18'], raise_if_not_found=False)
        view_odoo19 = env.ref(config['xmlid_19'], raise_if_not_found=False)

        # Activar vista correcta según versión
        if is_odoo18:
            if view_odoo18:
                view_odoo18.write({'active': True})
            if view_odoo19:
                view_odoo19.write({'active': False})
        else:
            if view_odoo18:
                view_odoo18.write({'active': False})
            if view_odoo19:
                view_odoo19.write({'active': True})


def _load_data_file(env, filename):
    """
    Carga un archivo XML de datos usando la API estándar de Odoo.

    Args:
        env: Odoo environment
        filename: Ruta relativa al archivo XML dentro del módulo
    """
    try:
        # Compatibilidad Odoo 18/19: kind fue deprecado en Odoo 19
        # Odoo 18: acepta kind='data'
        # Odoo 19: kind está deprecado, se omite
        tools.convert.convert_file(
            env,
            'industry_real_estate',
            filename,
            None,
            kind='data',
            mode='init'
        )
        _logger.info('Successfully loaded data file: %s', filename)
    except Exception as exc:
        _logger.error(
            'Failed to load data file %s: %s',
            filename,
            exc,
            exc_info=True
        )


def _post_init_load_version_specific_filters(env, is_odoo18):
    """
    Carga los filtros específicos de la versión de Odoo.

    Cambios en Odoo 19:
    - ir.filters: 'user_id' (Many2one) → 'user_ids' (Many2many)

    Estrategia:
    - Usamos la función genérica _load_data_file
    - El archivo se carga condicionalmente según la versión detectada
    - Referencia: odoo/addons/product_unspsc/hooks.py
    """
    # Determinar qué archivo cargar según la versión
    filter_filename = 'data/ir_filters_odoo18.xml' if is_odoo18 else 'data/ir_filters_odoo19.xml'

    # Cargar el archivo XML usando la función genérica
    _load_data_file(env, filter_filename)


