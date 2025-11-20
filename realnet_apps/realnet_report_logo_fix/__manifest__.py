# -*- coding: utf-8 -*-
{
    'name': 'RealNet - Fix Report Logo',
    'version': '18.0.1.0.0',
    'category': 'Technical',
    'summary': 'Corrige la visualización del logo en reportes PDF',
    'description': """
        Este módulo corrige el problema de que el logo de la compañía no se muestra
        en los reportes PDF usando image_data_uri() correctamente.
    """,
    'author': 'RealNet',
    'website': 'https://www.realnet.com',
    'depends': ['web'],
    'data': [
        'views/report_logo_fix.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
