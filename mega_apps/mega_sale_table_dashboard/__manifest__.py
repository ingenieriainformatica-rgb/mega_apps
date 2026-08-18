# -*- coding: utf-8 -*-
{
    "name": "Mega - Table Sales Dashboard",
    "version": "1.0",
    "sequence": -139,
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://mega.realnet.com.co/",
    "category": "MegaTecnicentro/SalesDashboard",
    "summary": "Dynamic sales board with KPIs, graphs and rankings",
    "depends": ["sale", "web", "account", "stock", "mega_account_move_business_fields"],
    "data": [
        "views/sale_dashboard_menu.xml",
        "views/account_journal.xml",
        "views/stock_warehouse_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            'mega_sale_table_dashboard/static/src/dashboard/**/*',
        ],
    },
    "application": False,
    "installable": True,
    "license": "LGPL-3",
}
