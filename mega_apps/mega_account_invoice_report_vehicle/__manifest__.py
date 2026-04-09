{
    'name': 'Mega Account Invoice Report Vehicle',
    'version': '18.0.1.0.0',
    'summary': 'Add the vehicle field to invoice analysis',
    "category": "MegaTecnicentro/ReportVehicle",
    'author': 'Jorge Alberto Quiroz Sierra',
    "website": "https://mega.realnet.com.co/",
    "sequence": -210,
    'depends': [
        'account',
    ],
    'data': [
        'views/account_invoice_report_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
