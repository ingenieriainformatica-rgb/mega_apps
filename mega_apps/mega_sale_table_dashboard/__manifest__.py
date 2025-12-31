# -*- coding: utf-8 -*-
{
    "name": "Mega - Table Sales Dashboard",
    "version": "1.0",
    "sequence": -139,
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://mega.realnet.com.co/",
    "category": "MegaTecnicentro/SalesDashboard",
    "summary": "Dynamic sales board with KPIs, graphs and rankings",
    "depends": ["sale", "web"],
    "data": [
        "views/sale_dashboard_menu.xml",
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
