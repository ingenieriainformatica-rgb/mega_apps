import logging
from odoo import http  #type: ignore
from odoo.http import request  #type: ignore

_logger = logging.getLogger(__name__)

WEBSITE_CODE_ID = 1  # MEGATECNICENTRO WEBSITE ID, REPLACE WITH YOUR OWN IF DIFFERENT


class LandingPage(http.Controller):

    @http.route('/mega-leads', type='http', auth='public', website=True)
    def landing(self, **kwargs):

        website_id = request.website.id

        if website_id != WEBSITE_CODE_ID:
            _logger.warning("Access denied to landing page")
            return request.redirect('/')  # o 404

        return request.render('mega_landing_page.mega_landing_leads')
