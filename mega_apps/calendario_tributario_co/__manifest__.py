# -*- coding: utf-8 -*-
{
    'name': 'Calendario Tributario Colombia - Alertas y Recordatorios',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'author': 'Tu Empresa',
    'depends': ['base', 'mail', 'account'],
    'data': [
        'security/ir.model.access.csv',
        # 'data/obligaciones_data.xml',
        # 'data/cron_data.xml',
        'views/obligacion_tributaria_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}  # type: ignore
