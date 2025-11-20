# -*- coding: utf-8 -*-
{
    'name': 'Realnet boton Comunicaciones',
    'summary': 'Floating WhatsApp/Chat/Call FAB for all website pages',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'author': 'Realnet',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'website_livechat',
    ],
    'assets': {
        'web.assets_frontend': [
            'realnet_boton_comunicaciones/static/src/scss/fab.scss',
            'realnet_boton_comunicaciones/static/src/js/fab.js',
        ],
    },
    'data': [
        'views/res_config_settings_views.xml',
        'views/website_contact_fab.xml',
    ],
    'installable': True,
    'application': False,
}
