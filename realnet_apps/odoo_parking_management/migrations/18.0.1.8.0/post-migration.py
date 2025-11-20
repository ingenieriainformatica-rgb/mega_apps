# -*- coding: utf-8 -*-

import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migration script to update vehicle_id constraint in parking.entry"""
    
    # The field constraint will be updated automatically by Odoo when the module is updated
    # due to the ondelete='set null' parameter in the field definition
    
    _logger.info("Migration 18.0.1.8.0: Updated vehicle_id constraint to allow deletion")
    
    # Optional: Log any existing entries that might be affected
    env = api.Environment(cr, SUPERUSER_ID, {})
    entries_count = env['parking.entry'].search_count([('vehicle_id', '!=', False)])
    _logger.info(f"Found {entries_count} parking entries with vehicle references")
