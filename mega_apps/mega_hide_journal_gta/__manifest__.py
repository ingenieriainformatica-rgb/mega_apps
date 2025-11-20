{
    'name': 'Mega - Hide GTA',
    'version': '1.0',
    'summary': 'Hide invoices with GTA status according to supplier group.',
    'description': """
        This module hides invoices with the status 'GTA' in the vendor invoice view,
        depending on whether the vendor belongs to a specific group.
    """,
    "author": "Jorge Alberto Quiroz Sierra",
    "sequence": -122,
    "category": "MegaTecnicentro/HideVat",
    "website": "https://mega.realnet.com.co/",
    'depends': ['account', 'base'],
    'data': [
        'security/group.xml',
        'views/account_journal_views.xml',
    ],
    "license": "LGPL-3",
    "application": False,
    "installable": True,
}
