# -*- coding: utf-8 -*-
{
    "name": "RL Product Ref Filler (Archived)",
    "summary": "Asigna default_code a productos archivados sin referencia",
    "version": "1.0",
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://mega.realnet.com.co/",
    "sequence": -116,
    "category": "MegaTecnicentro/Archived",
    "depends": ["stock", "product", "mail"],
    "data": [
        "security/group.xml",
        "security/ir.model.access.csv",
        "wizard/product_ref_fill_wizard_views.xml",
        "views/menu.xml",
    ],
    "license": "LGPL-3",
    "application": True,
    "installable": True,
}
