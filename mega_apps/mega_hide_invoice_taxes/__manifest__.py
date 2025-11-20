# -*- coding: utf-8 -*-
{
    "name": "Mega - Hide Taxes in Invoice PDF",
    "summary": "Hides the Taxes column and tax totals in the invoice PDF",
    "version": "1.0",
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://mega.realnet.com.co/",
    "sequence": -117,
    "category": "MegaTecnicentro/HideVat",
    "depends": ["account", "sale"],
    "data": [
        "views/report_invoice_hide_taxes.xml",
        "views/report_sale_hide_taxes.xml",
    ],
    "license": "LGPL-3",
    "application": True,
    "installable": True,
}
