{
    "name": "Mega - Security Inventory",
    "version": "1.0",
    "summary": "Restringe menús/acciones sensibles de Inventario por grupo",
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://mega.realnet.com.co/",
    "sequence": -150,
    "category": "MegaTecnicentro/InventorySecurity",
    "depends": ["stock"],
    "data": [
        "security/security.xml",
        "views/menu_restrict.xml",
        "views/product_views.xml",
        "views/barcode_restrict.xml",
    ],
    "application": True,
    "installable": True,
    "license": "LGPL-3",
}
