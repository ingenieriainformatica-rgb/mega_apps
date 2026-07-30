# -*- coding: utf-8 -*-
{
    'name': 'Payment Register - Multi Writeoff Lines',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Multiple writeoff lines in payment register wizard',
    'description': """
        Payment Register Multiple Writeoff Lines
        ==========================================

        Allows adding multiple writeoff lines with different accounts,
        amounts, and labels when registering payments.

        Features:
        - Multiple writeoff lines per payment
        - Automatic validation: sum must equal payment difference
        - Simple UI with inline editing
        - Backward compatible with standard mode
    """,
    'author': 'Variedades',
    'website': 'https://www.variedades.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_payment_register_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
