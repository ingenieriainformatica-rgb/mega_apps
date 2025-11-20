# -*- coding: utf-8 -*-
{
    'name': 'Realnet Anticipos',
    'summary': 'Anticipos clientes y proveedores con reclasificacion automatica',
    'version': '18.0.1.0.5',
    'author': 'Realnet',
    'website': 'https://www.realnet.com.co',
    'category': 'Accounting',
    'license': 'OEEL-1',
    'depends': ['base','account'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'description': 'Anticipos clientes y proveedores con reclasificacion automatica y deteccion robusta de pagos desde factura (v1.0.5).'
}
