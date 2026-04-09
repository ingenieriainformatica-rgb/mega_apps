# -*- coding: utf-8 -*-
{
    'name': 'Mega Account Customer Statement Email',
    'version': '18.0.1.0.0',
    'summary': 'Manual and automatic sending of portfolio receivable per client',
    'author': 'Jorge Alberto Quiroz Sierra',
    "sequence": -210,
    "category": "MegaTecnicentro/SendEmailCartera",
    "website": "https://mega.realnet.com.co/",
    'depends': [
        'account',
        'mail',
        'contacts',
    ],
    'data': [
        # 'security/ir.model.access.csv',
        # 'data/mail_template.xml',
        'data/ir_cron.xml',
        'views/res_partner_views.xml',
        # 'views/statement_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
