{
    'name': 'Mega - Landing Page - Leads',
    'version': '18.0.1.0',
    'author': 'Jorge Alberto Quiroz Sierra',
    'website': "https://megatecnicentro.com/",
    "category": "MegaTecnicentro/LandingPage",
    "sequence": -360,
    'depends': [
        'website',
        'mega_website_lead_demo'
    ],
    'data': [
        'views/landing_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'mega_landing_page/static/src/js/mega_lead_form.js',
        ],
    },
    "application": True,
    "installable": True,
    "license": "LGPL-3",
} # type: ignore
