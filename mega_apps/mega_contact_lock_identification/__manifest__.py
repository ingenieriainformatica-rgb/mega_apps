# -*- coding: utf-8 -*-
{
    "name": "Mega Contact Lock Identification",
    "version": "18.0.2.0.0",
    "category": "MegaTecnicentro/CRMCustom",
    'author': 'Jorge Alberto Quiroz Sierra',
    "website": "https://megatecnicentro.com/",
    "sequence": -320,
    "depends": [
        "contacts",
        "sale",
        "account",
        "l10n_latam_base",
        "l10n_co",
        "l10n_co_dian",
        "l10n_co_dian_no_partner_name_update",
    ],
    "data": [
        "security/group.xml",
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        "wizard/mega_contact_identification_correction_views.xml",
        "data/res_city_data.xml",
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}  # type: ignore
