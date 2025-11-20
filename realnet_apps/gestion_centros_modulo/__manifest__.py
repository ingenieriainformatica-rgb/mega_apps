
{
    "name": "Educational Management - Students and Centers",
    "version": "1.0",
   "summary": "Student and Educational Center Management",
    "description": """
        Module to manage students and educational centers independently.
        
        Features:
        - Full student management
        - Educational center management
        - Filters by Parents' Association (AMPA), activity, and center
        - Basic family data
    """,
    "author": "Andros Cabello",
    # "price":"4.99",
    "currency":"EUR",
    "category": "Contacts",
    "depends": ["base"],
    'data': [
        'security/ir.model.access.csv',
        'views/centro_educativo_views.xml',
        'views/alumno_views.xml',
        'views/menu_views.xml',
    ],
    "images": [
    "images/main_screenshot.jpg"
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    'translation_export': True,
}