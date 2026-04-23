{
    "name": "Mega Validator Token DIAN",
    "version": "18.0.1.0.0",
    "summary": "Validador de archivos DIAN contra facturas en Odoo",
    "category": "MegaTecnicentro/Accounting",
    "sequence": -290,
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://megatecnicentro.com/",
    "depends": [
        "account",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/group.xml",
        "views/token_dian_name_views.xml",
        "wizard/dian_token_upload_wizard.xml",
        "views/token_dian_file_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}  # type: ignore
