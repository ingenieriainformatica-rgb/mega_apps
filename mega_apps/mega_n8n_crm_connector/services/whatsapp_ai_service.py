from odoo.http import request  #type: ignore


def _get_n8n_payload():# -> Any | dict[Any, Any]:
        payload = request.get_json_data() or {}

        if isinstance(payload, dict) and isinstance(payload.get("params"), dict):
            return payload["params"]

        return payload
