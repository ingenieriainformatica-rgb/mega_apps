# -*- coding: utf-8 -*-
{
    "name": "Mega - Blocks the creation of attributes in products",
    "summary": "Prevents the creation of new attributes from the 'Attributes and Variants' tab of the product.",
    "version": "1.0",
    "sequence": -123,
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://mega.realnet.com.co/",
    "category": "MegaTecnicentro/HideProduct",
    "depends": [
        "product"
    ],
    "data": [
        "views/product_attribute_line_no_create_view.xml",
    ],
    "application": False,
    "installable": True,
    "license": "LGPL-3",
}
