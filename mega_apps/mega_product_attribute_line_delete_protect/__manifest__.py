{
    "name": "Mega Product Attribute Line Delete Protect",
    "version": "18.0.1.0.0",
    "summary": "Bloquea la eliminación de líneas de atributos a usuarios sin permiso especial.",
    "category": "MegaTecnicentro/Inventory",
    "sequence": -360,
    "website": "https://megatecnicentro.com/",
    "author": "Jorge Alberto Quiroz Sierra",
    "depends": ["product"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/product_template_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}  # type: ignore
