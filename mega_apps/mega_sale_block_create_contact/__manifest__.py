{
    'name': 'CRM Custom Services',
    'version': '18.0.1.0.0',
    'summary': 'Do not create contact from the sales module',
    "category": "MegaTecnicentro/SaleNotCreateContact",
    'author': 'Jorge Alberto Quiroz Sierra',
    "website": "https://mega.realnet.com.co/",
    "sequence": -190,
    'depends': ['sale'],
    'data': [
        'views/sale_views.xml'
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
