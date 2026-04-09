# -*- coding: utf-8 -*-
{
    'name': 'Sale Invoice Vehicle Map',
    'version': '18.0.1.0.0',
    'summary': 'Maps the vehicle field of the sales order to the customer invoice',
    "website": "https://mega.realnet.com.co/",
    'category': 'MegaTecnicentro/InvoiceVehicleMap',
    "author": "Jorge Alberto Quiroz Sierra",
    "sequence": -190,
    'depends': [
        'sale_management',
        'account',
    ],
    'data': [
        'views/account_move_views.xml',
        'views/show_vehicule_pdf.xml',
        'views/show_vehicule_list.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
