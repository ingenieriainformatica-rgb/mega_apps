# -*- coding: utf-8 -*-
{
    "name": "Mega Contact Lock Identification",
    "version": "18.0.1.0.0",
    "category": "MegaTecnicentro/CRMCustom",
    'author': 'Jorge Alberto Quiroz Sierra',
    "website": "https://megatecnicentro.com/",
    "sequence": -320,
    "depends": [
        "contacts",
        "l10n_latam_base",
        "l10n_co_dian",
        "l10n_co_dian_no_partner_name_update",
    ],
    "data": [
        "security/group.xml",
        "views/res_partner_views.xml",
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}  # type: ignore
