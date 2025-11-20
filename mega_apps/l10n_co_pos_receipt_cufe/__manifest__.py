# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Colombian POS - CUFE on Receipt',
    'version': '1.0.0',
    'category': 'Point of Sale',
    'summary': 'Add CUFE and QR code to POS receipt for Colombia',
    'authors': 'Realnet',
    'website': 'https://www.realnet.com.co',
    'description': """
        Adds electronic invoice CUFE and QR code to POS receipt.

        Features:
        - Shows CUFE when invoice is generated
        - Displays QR code with CUFE information
        - Compatible with Colombian DIAN requirements
        - Configurable per POS
    """,
    'depends': [
        'point_of_sale',
        'l10n_co_edi',          # Localización colombiana - Facturación electrónica DIAN
    ],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_co_pos_receipt_cufe/static/src/overrides/**/*',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
