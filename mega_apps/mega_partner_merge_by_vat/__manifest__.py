# -*- coding: utf-8 -*-
{
    "name": "Mega - Fusion de Contactos por VAT/NIT",
    "summary": "Deteccion y fusion asistida de contactos duplicados (VAT/NIT y nombre), con revision humana e historial persistente",
    "version": "18.0.1.0.0",
    "sequence": -106,
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://megatecnicentro.com/",
    "category": "MegaTecnicentro/Contactos",
    "depends": ["contacts", "account", "mail"],
    "data": [
        "security/partner_merge_security.xml",
        "security/ir.model.access.csv",
        "views/partner_merge_proposal_views.xml",
        "views/partner_merge_excluded_vat_views.xml",
        "views/partner_merge_detect_wizard_views.xml",
        "views/partner_merge_bulk_merge_wizard_views.xml",
        "views/menu.xml",
    ],
    "application": True,
    "installable": True,
    "license": "LGPL-3",
} #type: ignore
