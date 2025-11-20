# -*- coding: utf-8 -*-
{
    "name": "Mega - Contacts to UPPERCASE",
    "summary": "Tool to update contact names to UPPERCASE",
    "version": "1.0",
    "sequence": -105,
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://mega.realnet.com.co/",
    "category": "MegaTecnicentro/Contacts",
    "depends": ["contacts"],
    "data": [
        "security/partner_uppercase_security.xml",
        "security/ir.model.access.csv",
        "views/partner_uppercase_views.xml",
    ],
    "application": True,
    "installable": True,
    "license": "LGPL-3",
}
