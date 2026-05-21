# -*- coding: utf-8 -*-

from typing import Any

from odoo.http import request  # type: ignore


def get_n8n_payload() -> dict[str, Any]:
    """
    Extrae el payload enviado desde n8n.

    Soporta:
    1. JSON-RPC:
       {
           "jsonrpc": "2.0",
           "method": "call",
           "params": {...}
       }

    2. JSON directo:
       {
           "phone": "...",
           "message": "...",
           "phone_number_id": "..."
       }
    """
    payload = request.get_json_data() or {}

    if not isinstance(payload, dict):
        return {}

    params = payload.get("params")
    if isinstance(params, dict):
        return params

    return payload
