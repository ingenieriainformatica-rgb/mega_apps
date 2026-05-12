{
    "name": "Mega Vehicle Battery Catalog",
    "version": "18.0.1.0.0",
    "category": "MegaTecnicentro/Fleet",
    "author": "Jorge Alberto Quiroz Sierra",
    "sequence": -400,
    "depends": [
        'fleet',
        'product',
        'mega_vehicle_website_base'
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/battery_application_views.xml",
        "views/battery_catalog_import_wizard_views.xml",
        "views/battery_price_import_wizard_views.xml",
        "views/menu.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
} #type:ignore
