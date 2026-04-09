from datetime import datetime


def post_init_hook_zone(env):
    Zone = env['crm.home.zone']

    zonas = [

        # Comunas principales
        'Medellín - El Poblado',
        'Medellín - Laureles',
        'Medellín - Belén',
        'Medellín - Robledo',
        'Medellín - Castilla',
        'Medellín - Aranjuez',
        'Medellín - Buenos Aires',
        'Medellín - Guayabal',
        'Medellín - San Javier',
        'Medellín - Centro',

        # Municipios Valle de Aburrá
        'Envigado',
        'Itagüí',
        'Sabaneta',
        'Bello',
        'Caldas',
        'La Estrella',
        'Copacabana',
        'Girardota',
        'Barbosa',
    ]

    existentes = set(Zone.search([]).mapped('name'))

    nuevos = []
    for zona in zonas:
        if zona not in existentes:
            nuevos.append({'name': zona})

    if nuevos:
        Zone.create(nuevos)

def post_init_hook_year(env):
    Year = env['crm.lead.year']
    current_year = datetime.now().year

    existing_years = set(Year.search([]).mapped('year'))
    vals_list = []

    for year in range(1950, current_year + 1):
        if year not in existing_years:
            vals_list.append({'year': year})

    if vals_list:
        Year.create(vals_list)


def post_init_hook(env):
    post_init_hook_year(env)
    post_init_hook_zone(env)
