{
    'name': 'Mega - Label Change in Vendor Bills',
    'version': '1.0',
    'summary': 'Updates the label of the field "Untaxed Amount in Signed Currency" in the vendor bills view.',
    'description': """
    Lightweight module to adjust the visible label of the field `amount_untaxed_in_currency_signed`
    in vendor bills (model `account.move`).
    """,
    'author': 'Jorge Alberto Quiroz Sierra',
    'website': 'https://mega.realnet.com.co/',
    "category": "MegaTecnicentro/ChangeLabel",
    "sequence": -108,
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
        'views/account_move_client_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
