# -*- coding: utf-8 -*-
{
    "name": "Mega Account Move Business Fields",
    "summary": "Campo Concepto gestionado por código (mega_concepto) como reemplazo del campo de Studio x_studio_concepto",
    "version": "18.0.1.0.0",
    "sequence": -140,
    "category": "MegaTecnicentro/Concept",
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://megatecnicentro.com/",
    "depends": [
        "account",
    ],
    "data": [
        "views/account_move_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
} # type:ignore
