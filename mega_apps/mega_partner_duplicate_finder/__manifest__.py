# -*- coding: utf-8 -*-
{
    "name": "Mega Partner Duplicate Finder",
    "version": "18.0.1.0.0",
    "summary": "Detecta contactos repetidos en Contactos por documento y/o nombre",
    "category": "MegaTecnicentro/Contacts",
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://megatecnicentro.com/",
    "sequence": -270,
    "depends": [
        "contacts",
    ],
    "data": [
        "security/group.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "views/partner_duplicate_line_views.xml",
        "views/partner_duplicate_group_views.xml",
        "views/partner_duplicate_batch_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}  # type: ignore
