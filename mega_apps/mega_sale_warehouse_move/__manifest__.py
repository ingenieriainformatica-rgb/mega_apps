# -*- coding: utf-8 -*-
{
    "name": "Mega - Move warehouse in sales order",
    "summary": "Relocates the Warehouse field to the 'Other information' tab of the sales order.",
    "version": "1.0",
    "sequence": -122,
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://mega.realnet.com.co/",
    "category": "MegaTecnicentro/Sales",
    "depends": [
        "sale",   # donde está la vista principal de sale.order
        "sale_stock"
    ],
    "data": [
        "views/sale_order_view.xml",
    ],
    "application": False,
    "installable": True,
    "license": "LGPL-3",
}
