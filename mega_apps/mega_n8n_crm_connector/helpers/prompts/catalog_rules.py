from textwrap import dedent


def get_catalog_rules() -> str:
    return dedent(
        """
        # CATÁLOGO Y BATERÍAS

        Si current_step es "catalog_sent" o "more_catalog_sent":
        - No inventes precios.
        - No calcules recargos.
        - No generes links de pago.
        - Solo interpreta intención del cliente.

        Intents permitidos:
        - accept_recommended_battery
        - ask_price_without_old_battery
        - request_more_options
        - request_advisor
        - select_catalog_option
        - confirm_data_correct
        - correct_data
        - unknown

        Batería usada:
        - Si el cliente dice que entrega/deja/devuelve la batería usada:
          customer_leaves_old_battery = true
        - Si dice que conserva/se queda con/no entrega la batería usada:
          customer_leaves_old_battery = false
        - Si no es claro:
          customer_leaves_old_battery = true

        Si el cliente elige una opción del catálogo adicional:
        - intent = "select_catalog_option"
        - selected_catalog_option debe ser 1, 2 o 3.
        """
    ).strip()

