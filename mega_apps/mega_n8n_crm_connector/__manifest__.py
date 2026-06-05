{
    "name": "Mega n8n CRM Connector",
    "version": "18.0.1.0.0",
    "category": "MegaTecnicentro/CrmN8n",
    "sequence": -410,
    "summary": "Endpoints para integrar n8n con CRM y Contactos",
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://mega.realnet.com.co/",
    "depends": [
        "base",
        "crm",
        "queue_job",
        "whatsapp",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/queue_job_data.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
} #type:ignore
