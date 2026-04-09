# -*- coding: utf-8 -*-
{
    "name": "Partner Ledger Dashboard (Terceros)",
    "version": "1.0",
    "sequence": -155,
    "author": "Jorge Alberto Quiroz Sierra",
    "category": "MegaTecnicentro/Ledger",
    "website": "https://mega.realnet.com.co/",
    "depends": ["web", "account", "mega_sale_table_dashboard"],
    "data": [
        "views/partner_ledger_menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mega_partner_ledger_dashboard/static/src/third_parties/**/*",
        ],
    },
    "application": False,
    "installable": True,
    "license": "LGPL-3",
}
