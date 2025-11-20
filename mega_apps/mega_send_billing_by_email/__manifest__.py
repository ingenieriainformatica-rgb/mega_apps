{
    "name": "Mega - Alert Facturas",
    "version": "1.0",
    "summary": "Envía alertas por correo sobre facturas diariamente",
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://mega.realnet.com.co/",
    "sequence": -122,
    "category": "MegaTecnicentro/Alertfacturas",
    "depends": ["base", "mail", "account"],
    "data": [
        # "security/ir.model.access.csv",
        "security/group.xml",
        "data/cron_data.xml",
        "data/mail_template.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
