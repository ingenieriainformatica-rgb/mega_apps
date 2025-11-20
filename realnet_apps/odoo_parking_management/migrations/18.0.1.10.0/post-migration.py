from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Set new site config 'slot_required' to True on existing sites

    Prior to this version, slot assignment was always mandatory. We preserve
    that behavior by enabling the flag on all existing records.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    sites = env['parking.site'].search([])
    if sites:
        sites.write({'slot_required': True})

