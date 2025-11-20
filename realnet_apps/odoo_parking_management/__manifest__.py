
{
    'name': 'Parking Management',
    'version': '18.0.1.10.0',  # Per-site optional slot assignment
    'category': 'Industries',
    'summary': 'Manage the parking of vehicles with site-based security',
    'description': """This module is developed for managing the vehicle 
    parking and providing the parking tickets for any type of customers.
    
    Features:
    - Multi-site parking management (Medellín, Cúcuta, Bogotá)
    - Site-based security and access control
    - Operator role with restricted access to assigned sitesyu6
    - Admin role with full access to all sites
    - Integrated accounting with site-based analytics
    - Monthly contracts for regular customers
    - Monthly dashboard with metrics by site
    - Automatic invoice aggregation for monthly customers
    - CRON jobs for automated billing and processing
    """,
    'author': 'Realnet, Cybrosys Techno Solutions',
    'company': 'Realnet',
    'maintainer': 'Realnet',
    'website': 'https://www.realnet.com.co',
    'depends': ['base', 'fleet', 'account', 'project'],
    'data': [
        'security/odoo_parking_management_groups.xml',
        'security/parking_entry_security.xml',
        'security/ir.model.access.csv',
        'data/report_paperformat_data.xml',
        'data/ir_sequence_data.xml',
        'data/parking_site_data.xml',  # Site data for 15 locations
        'data/location_details_data.xml',  # Location data for each site
        'data/monthly_setup_data.xml',  # Monthly parking setup
        'data/monthly_cron_data.xml',  # Monthly parking cron jobs
        # 'data/product_data.xml',  # Temporarily disabled - products can be created manually
        'data/migration_data.xml',  # Migration data for customer_type consolidation
        # 'data/menu_fix_data.xml',  # Force menu fixes for private/public consolidation - DISABLED
        'report/parking_ticket_report_templates.xml',
        'wizard/register_payment_views.xml',
        # Load root menus before any views that reference them
        'views/parking_entry_views.xml',
        'views/parking_site_views.xml',  # Site management views
        'views/parking_reference_views.xml',  # Pricing references (Convenios)
        'views/res_users_views.xml',  # User extensions for site access
        'views/slot_type_views.xml',
        'views/location_details_views.xml',
        'views/slot_details_views.xml',
        'views/member_slot_reservation_views.xml',
        'views/vehicle_details_views.xml',
        'views/parking_monthly_contract_views.xml',  # Monthly contracts
        'views/parking_authorized_vehicle_views.xml',  # Authorized plates inline views
        'views/parking_suspicious_vehicle_views.xml',  # Suspicious vehicles alerts
        'views/parking_monthly_dashboard_views.xml',  # Monthly dashboard
        'views/parking_monthly_menus.xml',  # Monthly parking menus
        'views/parking_regular_dashboard_views.xml',  # Regular customers dashboard
        'views/parking_regular_menus.xml',  # Regular dashboard menu under Reporting
        'views/parking_operational_dashboard_views.xml',  # Operational dashboard (unified)
        'views/parking_operational_menus.xml',  # Menu for operational dashboard
        'views/parking_operational_graphs.xml',  # Graph views for Operational dashboard
    ],
    'demo': [
        'data/demo_users_data.xml',  # Demo users with site assignments
    ],
    'images': ['static/description/banner.jpg'],
    'assets': {
        'web.assets_backend': [
            'odoo_parking_management/static/src/js/payment_wizard_guard.js',
            'odoo_parking_management/static/src/css/payment_wizard_guard.css',
            'odoo_parking_management/static/src/js/slot_type_icons.js',
            'odoo_parking_management/static/src/css/slot_type_icons.css',
            'odoo_parking_management/static/src/js/home_menu_filter.js',
        ],
        'web.assets_web': [
            # Also load the widget in generic web bundle to avoid race/missing widget
            'odoo_parking_management/static/src/js/slot_type_icons.js',
            'odoo_parking_management/static/src/css/slot_type_icons.css',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
    'post_init_hook': 'post_init_hook',
    'pre_init_hook': 'pre_init_hook',
}

