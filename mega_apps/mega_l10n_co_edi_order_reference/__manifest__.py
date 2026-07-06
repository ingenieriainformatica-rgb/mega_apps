# -*- coding: utf-8 -*-
{
    'name': "Mega L10n CO EDI - Order Reference condicional",
    'summary': "Envia cac:OrderReference (N. orden) en el XML DIAN solo para ALFRED SAS.",
    'author': "Realnet",
    'website': 'https://www.realnet.com.co',
    'category': 'Accounting/Localizations/EDI',
    'version': '18.0.1.0.0',
    'depends': [
        'l10n_co_dian',
        'mega_invoice_order_number_report',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
