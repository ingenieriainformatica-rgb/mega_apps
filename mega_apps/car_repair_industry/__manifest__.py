# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    "name": "Mega - Taller",
    "version": "1.0",
    "depends": ['base', 'sale', 'purchase', 'account', 'sale_stock', 'mail', 'product', 'stock', 'fleet','sale_management', 'website', 'calendar', 'hr_timesheet','web'],
    "author": "BROWSEINFO",
    "summary": "Fleet repair vehicle repair car Maintenance auto-fleet service repair Car Maintenance Repair workshop automobile repair Automotive Service repair Automotive repair machine repair workshop equipment repair service Repair auto repair shop Auto Shop repair",
    "description": """
        Repairs Management
        Maintenance & Repairs Management
        auto repair shop management software

        auto repair software free
        auto service
        auto spareparts
        auto repair industry

        automotive workshop management software

    """,
    'category': 'MegaTecnicentro/Taller',
    'price': 129,
    'currency': "EUR",
    "website": "https://www.browseinfo.com/demo-request?app=car_repair_industry&version=19&edition=Community",
    "data": [
        'security/fleet_repair_security.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'data/mail_template_data.xml',
        'wizard/fleet_repair_assign_to_head_tech_view.xml',
        'wizard/fleet_diagnose_assign_to_technician_view.xml',
        'views/fleet_repair_view.xml',
        'views/fleet_repair_service_checklist_view.xml',
        'views/fleet_repair_sequence.xml',
        'views/fleet_diagnose_view.xml',
        'views/fleet_workorder_sequence.xml',
        'views/fleet_vehicle_model_views_inherit.xml',
        'views/fleet_workorder_view.xml',
        'views/custom_sale_view.xml',
        'views/calendar_event_view.xml',
        'views/appointment_slots_views.xml',
        'views/fleet_vehicle_model_view.xml',
        'views/dashboard.xml',
        'views/templates.xml',
        'views/fleet_vehicle_view.xml',
        'report/fleet_repair_label_view.xml',
        'report/fleet_repair_label_menu.xml',
        'report/fleet_repair_receipt_view.xml',
        'report/fleet_repair_receipt_menu.xml',
        'report/fleet_repair_checklist_view.xml',
        'report/fleet_repair_checklist_menu.xml',
        'report/fleet_diagnostic_request_report_view.xml',
        'report/fleet_diagnostic_request_report_menu.xml',
        'report/fleet_diagnostic_result_report_view.xml',
        'report/fleet_diagnostic_result_report_menu.xml',
        'report/fleet_workorder_report_view.xml',
        'report/fleet_workorder_report_menu.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'car_repair_industry/static/src/css/custom.css',
            'car_repair_industry/static/src/js/slot_time.js',
        ],
        'web.assets_backend': [
            'car_repair_industry/static/src/js/fleet_repair_dashboard.js',
            'car_repair_industry/static/src/xml/**/*',
        ],
    },
    'qweb': [
    ],
    "auto_install": False,
    "installable": True,
    'live_test_url': 'https://www.browseinfo.com/demo-request?app=car_repair_industry&version=19&edition=Community',
    "images": ['static/description/Banner.gif'],
    "license": 'OPL-1',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
