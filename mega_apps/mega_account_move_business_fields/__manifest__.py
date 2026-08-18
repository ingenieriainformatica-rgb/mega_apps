# -*- coding: utf-8 -*-
{
    "name": "Mega Account Move Business Fields",
    "summary": "Campos Concepto y Descripción general gestionados por código (mega_concepto, mega_descripcion_general) como reemplazo de los campos de Studio x_studio_concepto y x_studio_descripcin_1",
    "version": "18.0.1.0.1",
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
