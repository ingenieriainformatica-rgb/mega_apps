{
    'name': 'Mega - Invoicing Show VAT',
    'summary': 'Displays VAT amount separately in vendor bills and customer invoices list views.',
    'version': '1.0',
    'author': 'Jorge Alberto Quiroz Sierra',
    "website": "https://mega.realnet.com.co/",
    "sequence": -111,
    "category": "MegaTecnicentro/ShowVatInvoicing",
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
    ],
  "application": True,
  "installable": True,
  "license": "LGPL-3",
}
