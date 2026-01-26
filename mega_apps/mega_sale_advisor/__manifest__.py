# -*- coding: utf-8 -*-
{
    "name": "Mega Sale Advisor",
    "version": "1.0",
    "category": "MegaTecnicentro/SalesAsesor",
    "summary": "Mark contacts as advisors and allow them to be selected in Sales Orders.",
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://mega.realnet.com.co/",
    "sequence": -151,
    "depends": [
        "sale",
        "contacts",
    ],
    "data": [
        "views/res_partner_view.xml",
        "views/sale_order_view.xml",
        "views/account_move_view.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
