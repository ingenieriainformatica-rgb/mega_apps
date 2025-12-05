{
    "name": "Transfers Cash Custom",
    "version": "1.0",
    "summary": "Transferencias entre cajas",
    "author": "Jorge Alberto Quiroz Sierra",
    "category": "MegaTecnicentro/TransladosInternos",
    "website": "https://mega.realnet.com.co/",
    "depends": ["account"],
    "data": [
        'security/groups.xml',
        'security/ir.model.access.csv',
        "views/account_move_cash_views.xml",
        "views/account_journal_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": True,
}
