import logging
from typing import Any
from urllib.parse import parse_qs, urlparse

from odoo.http import request  # type: ignore

_logger = logging.getLogger(__name__)


def _extract_all_url_params(httprequest, website_url):
    full_url = website_url
    path_url = httprequest.path

    parsed_url = urlparse(full_url)
    all_params = parse_qs(parsed_url.query)

    clean_params = {}
    for key, value in all_params.items():
        if isinstance(value, list):
            clean_params[key] = value[0] if len(value) == 1 else value[0]
        else:
            clean_params[key] = value

    utm_ids = {
        'source_id': _get_or_create_utm('utm.source', clean_params.get('utm_source')),
        'medium_id': _get_or_create_utm('utm.medium', clean_params.get('utm_medium')),
        'campaign_id': _get_or_create_utm('utm.campaign', clean_params.get('utm_campaign')),
    }

    return {
        'params': clean_params,
        'utm_ids': utm_ids,
        'full_url': full_url,
        'path_url': path_url,
        'referrer': httprequest.referrer or '',
        'user_agent': httprequest.user_agent.string or '',
        'remote_addr': httprequest.remote_addr or '',
    }


def _get_or_create_utm(model_name, value):
    if isinstance(value, list):
        value = value[0] if value else None
    if not value:
        return False

    value = str(value).strip()
    if not value:
        return False

    record = request.env[model_name].sudo().search([
        ('name', 'ilike', value)
    ], limit=1)

    if record:
        return record.id

    new_record = request.env[model_name].sudo().create({'name': value})
    return new_record.id
