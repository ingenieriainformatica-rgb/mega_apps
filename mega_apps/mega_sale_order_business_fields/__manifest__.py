# -*- coding: utf-8 -*-
{
    "name": "Mega Sale Order Business Fields",
    "summary": "Campo Descripción gestionado por código (mega_descripcion) como reemplazo del campo de Studio x_studio_descripcion",
    "version": "18.0.1.0.0",
    "sequence": -140,
    "category": "MegaTecnicentro/Concept",
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://megatecnicentro.com/",
    "depends": [
        "sale",
    ],
    "data": [
        "views/sale_order_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
} # type:ignore
