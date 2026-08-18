# -*- coding: utf-8 -*-
{
    "name": "Mega - Concept in Invoice Analysis", 
    "summary": "Add the Concept field (mega_concepto) of the invoice to the account.invoice.report",
    "sequence": -138,
    "version": "1.0",
    "category": "MegaTecnicentro/Concept",
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://mega.realnet.com.co/",
    "depends": ["account", "mega_account_move_business_fields"],
    "data": [
        # "security/ir.model.access.csv",
        "views/account_invoice_report_views.xml",
    ],
    "license": "LGPL-3",
    "application": False,
    "installable": True,
}
