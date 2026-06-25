# -*- coding: utf-8 -*-
{
    'name': 'Mega Invoice Order Number Report',
    'version': '18.0.1.0.0',
    'summary': 'Agrega N° orden del cliente en factura y lo muestra en el PDF',
    'category': 'MegaTecnicentro/Invoice',
    'author': 'Jorge Alberto Quiroz Sierra',
    'website': 'https://mega.realnet.com.co/',
    'sequence': -200,
    'depends': [
        'account',
    ],
    'data': [
        'views/account_move_views.xml',
        'report/report_invoice_order_number.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
