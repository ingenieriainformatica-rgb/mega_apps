# -*- coding: utf-8 -*-
{
    'name': "Mega L10n CO EDI - Order Reference condicional",
    'summary': "Envia cac:OrderReference en el XML DIAN solo si el cliente lo tiene habilitado y la factura tiene N° orden.",
    'author': "Realnet",
    'website': 'https://www.realnet.com.co',
    'category': 'Accounting/Localizations/EDI',
    'version': '18.0.1.0.0',
    'depends': [
        'l10n_co_dian',
        'mega_invoice_order_number_report',
    ],
    'data': [
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
