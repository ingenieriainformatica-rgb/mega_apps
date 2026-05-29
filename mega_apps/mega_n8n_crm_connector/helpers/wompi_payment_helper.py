# -*- coding: utf-8 -*-
import logging
import requests

_logger = logging.getLogger(__name__)

WOMPI_API_URL = "https://production.wompi.co/v1/payment_links"
WOMPI_CHECKOUT_URL = "https://checkout.wompi.co/l/{link_id}"

# WOMPI_API_URL = "https://sandbox.wompi.co/v1/payment_links"

def create_wompi_payment_link(
    private_key: str,
    name: str,
    description: str,
    amount: float,
    single_use: bool = True,
    collect_shipping: bool = False,
) -> dict:

    private_key = (private_key or "").strip()

    if not private_key:
        return {
            "success": False,
            "error": "No hay llave privada de Wompi configurada.",
            "payment_url": "",
        }

    amount_in_cents = int(round(float(amount or 0) * 100))

    if amount_in_cents <= 0:
        return {
            "success": False,
            "error": "El valor del pago debe ser mayor a cero.",
            "payment_url": "",
        }

    payload = {
        "name": name[:80],
        "description": description[:250],
        "single_use": single_use,
        "collect_shipping": collect_shipping,
        "currency": "COP",
        "amount_in_cents": amount_in_cents,
    }

    headers = {
        "Authorization": f"Bearer {private_key}",
        "Content-Type": "application/json",
    }

    response = None

    try:
        response = requests.post(
            WOMPI_API_URL,
            json=payload,
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as error:
        _logger.exception("[WOMPI] Error creando link de pago")
        return {
            "success": False,
            "error": str(error),
            "status_code": response.status_code if response else False,
            "response": response.text if response else "",
            "payment_url": "",
        }
    except ValueError as error:
        _logger.exception("[WOMPI] Respuesta inválida creando link de pago")
        return {
            "success": False,
            "error": str(error),
            "status_code": response.status_code if response else False,
            "response": response.text if response else "",
            "payment_url": "",
        }

    link_id = data.get("data", {}).get("id")

    if not link_id:
        return {
            "success": False,
            "error": "Wompi no retornó ID del link de pago.",
            "payment_url": "",
            "raw": data,
        }

    return {
        "success": True,
        "payment_link_id": link_id,
        "payment_url": WOMPI_CHECKOUT_URL.format(link_id=link_id),
        "raw": data,
    }
