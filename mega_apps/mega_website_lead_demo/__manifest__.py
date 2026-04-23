{
    'name': 'Website Lead Demo',
    'version': '18.0.1.0.0',
    "category": "MegaTecnicentro/Website",
    'summary': 'Website Lead Demo',
    "sequence": -250,
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://megatecnicentro.com/",
    'depends': ['website', 'crm', 'fleet'],
    'data': [
        'views/website_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'mega_website_lead_demo/static/src/css/lead_demo_modal.css',
            'mega_website_lead_demo/static/src/js/website_lead_modal.js',
        ],
    },
    "application": False,
    "installable": True,
    "license": "LGPL-3",
} # type: ignore
