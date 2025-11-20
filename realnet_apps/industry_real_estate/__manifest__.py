{
    'name': 'ECO-ERP',
    'version': '1.1',
    'category': 'Services',
    'depends': [
        # CRM / Website (solo si los usas)
        'sale_crm',
        'website_crm',
        'website_studio',          # para desarrollo en línea
        # Ventas / Contabilidad / Productos / Propiedades
        'product',
        'account',
        'accountant',
        'analytic',
        'stock',
        'repair',
        # Suscripciones / Proyectos 
        'sale_subscription',       # si usas suscripciones
        'project',                 # si usas proyectos
        'sale_project',
        'sale_management',        
        # Firma y Documentos
        'sale',
        'mail',
        'purchase', 
        'base',
        'contacts',
        'sign',
        'web',
        'documents',
        'documents_sign',
        # Enterprise extra
        'crm_enterprise',
        'crm_iap_enrich',
        'crm_iap_mine',
        'knowledge',
        'l10n_latam_base',
        'l10n_co_edi_mandate',     # modulo de mandatos
        # Quita si ya no lo usas:
        # 'base_automation',        # se retira debido a cambios necesarios para la correcta funcionalidad (se migraron a modelos de python (como debe ser))
    ],
    'data': [
        # 1) Seguridad y datos base
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_model.xml',
        'data/ir_model_fields.xml',
        'data/ir_model_2.xml',
        'data/account_analytic_plan.xml',
        'data/crm_stages.xml',        
        'data/ir_attachment_pre.xml',
        'data/product_product.xml',
        'data/sale_order_template.xml',
        'data/contract_template.xml',
        'data/knowledge_cover.xml',
        'data/knowledge_article.xml',
        'data/knowledge_article_favorite.xml',
        'data/mail_message.xml',        
        # 2) Vistas (todas ANTES de acciones/menús)
        'data/asset_sign_redirect.xml',
        'data/ir_ui_views.xml',
        'views/product_view.xml',
        'views/property_form_view.xml',
        'views/property_delivery_recepcion_form.xml',
        'views/property_inventory_tab.xml',
        'views/property_reception_tab.xml',
        'views/property_delivery_tab.xml',
        'views/confirm_reception_wizard.xml',
        'views/property_item_history_tree.xml',
        'views/x_contract_views.xml',
        'views/sale_order_inherit_contract_tab.xml',
        'views/sale_order_form_owner_inherit.xml',
        'views/rental_form_vigencia_view.xml',
        'views/contract_excel_wizard_views.xml',
        'views/contract_excel_import_wizard_views.xml',
        'views/ipc_history_views.xml',
        'views/create_bill_view.xml',
        'views/res_partner_view.xml',
        'views/contract_history_adjustment_views.xml',
        'views/account_move_inherit_views.xml',
        'views/utilities_import_wizard_views.xml',
        # 3) Reportes (si no referencian acciones/menús)
        'reports/contract.xml',
        'reports/report_contract_preview_template.xml',
        'reports/report_contract_preview.xml',
        'reports/action_contract.xml',
        # 4) Acciones (después de vistas)
        'data/ir_actions_server.xml',
        'data/ir_actions_act_window.xml', 
        # 5) Filtros que referencian vistas de búsqueda
        'data/ir_filters.xml',
        # NOTA: ir_filters_odoo18.xml y ir_filters_odoo19.xml se cargan dinámicamente
        # desde el hook post_init_set_odoo_version_views() según la versión detectada
        # 6) Menús (después de acciones)
        'data/menu_item.xml',
        'views/res_config_settings_view.xml',
        'data/res_config_setting.xml',
        # 7) Website (si aplica, suelen referenciar vistas/acciones ya creadas)
        'data/website_controller_page.xml',
        'data/website_menu.xml',
        'data/website_view.xml',
        'data/website_theme_apply.xml',
        # 8) Otros datos que no referencien vistas/acciones
        # 'data/base_automation.xml',
        'data/ir_model_access.xml',
        'data/ir_rule.xml',
        'data/x_meters.xml',
        'data/knowledge_tour.xml',
        'data/ir_attachment_post.xml',
        'data/ir_cron.xml',
    ],
    'post_init_hook': 'post_init_all',
    'license': 'OPL-1',
    'assets': {
        'web.assets_backend': [
            'industry_real_estate/static/src/js/camera_widget.js',
            'industry_real_estate/static/src/js/my_tour.js',
            'industry_real_estate/static/src/xml/camera_widget.xml',
            'industry_real_estate/static/src/css/condition_badge.css',
            "industry_real_estate/static/src/js/eco_clause_variable_inserter.js",
            "industry_real_estate/static/src/css/eco_clause_variable_palette.css",
            'industry_real_estate/static/src/js/sign_redirect.js',
            'industry_real_estate/static/src/css/gantt_colors.css',
        ],
        'web.assets_qweb': [
            'industry_real_estate/static/src/xml/camera_widget.xml',
        ],
        'web.assets_frontend': [
            'industry_real_estate/static/src/js/sign_redirect.js',
        ]      
    },
    'author': 'Realnet',
    "cloc_exclude": [
        "data/knowledge_article.xml",
        "data/website_view.xml",
        "data/website_controller_page.xml",
        "static/src/js/my_tour.js",
        "demo/website_view.xml",
    ],
    'images': ['images/main.png'],
    'installable': True,
    'application': True,    
}
