# -*- coding: utf-8 -*-
{
    'name': 'Account Due Date Real Column',
    'version': '18.0.1.0.0',
    'summary': 'Add a column with the actual expiration date of the invoice',
    "category": "MegaTecnicentro/ColumnInvoice",
    'author': 'Jorge Alberto Quiroz Sierra',
    "sequence": -190,
    "website": "https://mega.realnet.com.co/",
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
