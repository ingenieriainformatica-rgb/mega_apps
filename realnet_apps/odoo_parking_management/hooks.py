# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#   This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Post-init hook to set up monthly parking functionality (Odoo 18 uses env)"""
    # Ensure we operate as superuser
    env = env(user=SUPERUSER_ID)
    
    try:
        # Check if setup is already complete
        setup_complete = env['ir.config_parameter'].sudo().get_param(
            'parking.monthly.setup.complete', 'False'
        )
        
        if setup_complete == 'True':
            _logger.info("Monthly parking setup already completed")
            return
        
        # Create default monthly parking products if they don't exist
        _create_monthly_products(env)
        
        # Set analytic accounts for sites if they don't have them
        _setup_site_analytics(env)
        
        # Backfill historical entries if needed
        _backfill_monthly_entries(env)
        
        # Mark setup as complete
        env['ir.config_parameter'].sudo().set_param(
            'parking.monthly.setup.complete', 'True'
        )
        
        _logger.info("Monthly parking setup completed successfully")
        
    except Exception as e:
        # Log full traceback and re-raise so Odoo rolls back cleanly
        _logger.exception("Error during monthly parking setup")
        raise


def _create_monthly_products(env):
    """Create default monthly parking products"""
    
    # Monthly parking plans
    products_data = [
        {
            'name': 'Monthly Parking - Auto',
            'type': 'service',
            'list_price': 200000.0,  # 200,000 COP
            'sale_ok': True,
            'purchase_ok': False,
            'categ_id': env.ref('product.product_category_all').id,
        },
        {
            'name': 'Monthly Parking - Moto',
            'type': 'service',
            'list_price': 100000.0,  # 100,000 COP
            'sale_ok': True,
            'purchase_ok': False,
            'categ_id': env.ref('product.product_category_all').id,
        },
    ]
    
    for product_data in products_data:
        existing = env['product.product'].search([
            ('name', '=', product_data['name'])
        ], limit=1)
        
        if not existing:
            env['product.product'].create(product_data)
            _logger.info(f"Created monthly product: {product_data['name']}")


def _get_default_analytic_plan(env):
    """Return a reasonable default Analytic Plan record.

    Tries the configured project plan; falls back to first root plan; creates one if none exist.
    """
    ICP = env['ir.config_parameter'].sudo()
    plan_id_str = ICP.get_param('analytic.project_plan')
    plan = None
    if plan_id_str and plan_id_str.isdigit():
        plan = env['account.analytic.plan'].browse(int(plan_id_str)).exists()
    if not plan:
        plan = env['account.analytic.plan'].search([('parent_id', '=', False)], limit=1)
    if not plan:
        plan = env['account.analytic.plan'].create({'name': 'Project'})
        ICP.set_param('analytic.project_plan', str(plan.id))
    return plan


def _setup_site_analytics(env):
    """Set up analytic accounts for parking sites, ensuring required plan_id is set"""
    plan = _get_default_analytic_plan(env)
    sites = env['parking.site'].search([])

    for site in sites:
        if not site.analytic_account_id:
            # Try to find existing analytic account on the same plan/company
            analytic = env['account.analytic.account'].search([
                ('name', 'ilike', f'Parking {site.name}'),
                ('plan_id', '=', plan.id),
                ('company_id', '=', site.company_id.id or env.company.id),
            ], limit=1)

            if not analytic:
                # Create new analytic account with required plan
                analytic_vals = {
                    'name': f'Parking {site.name}',
                    'code': f'PARK-{site.id}',
                    'plan_id': plan.id,
                    'company_id': site.company_id.id or env.company.id,
                }
                analytic = env['account.analytic.account'].create(analytic_vals)
                _logger.info(f"Created analytic account for site: {site.name} (plan {plan.display_name})")

            site.analytic_account_id = analytic.id


def _backfill_monthly_entries(env):
    """Backfill monthly entries that need to be computed"""
    
    # Trigger computation of is_monthly for all entries
    entries = env['parking.entry'].search([])
    
    if entries:
        _logger.info(f"Computing monthly status for {len(entries)} parking entries")
        # This will trigger the compute method for is_monthly
        entries._compute_is_monthly()
        
        # Process pending monthly entries
        monthly_service = env['parking.monthly.service']
        processed = monthly_service.process_pending_monthly_entries()
        
        if processed > 0:
            _logger.info(f"Processed {processed} pending monthly entries")


def pre_init_hook(env):
    """Pre-init hook for any database preparation (Odoo 18 uses env)"""
    # Nothing to do pre-init for now
    return None
