# -*- coding: utf-8 -*-
{
    'name': 'Credit Note Copy Invoice Data',
    'version': '18.0.1.0.0',
    'summary': 'Copia el campo Vehículo de la factura a la nota crédito generada desde ella',
    'website': 'https://mega.realnet.com.co/',
    'category': 'MegaTecnicentro/InvoiceVehicleMap',
    'author': 'Jorge Alberto Quiroz Sierra',
    'sequence': -189,
    'depends': [
        'account',
        'mega_sale_invoice_vehicle_map',
    ],
    'data': [
        'security/credit_note_vehicle_backfill_security.xml',
        'security/ir.model.access.csv',
        'wizard/credit_note_vehicle_backfill_wizard_views.xml',
        'views/credit_note_vehicle_backfill_menu.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
