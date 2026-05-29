from textwrap import dedent


def get_flow_rules() -> str:
    return dedent(
        """
        # FLUJO

        Pasos válidos:
        - ask_name
        - ask_vehicle
        - ask_location
        - confirm_data
        - catalog_sent
        - more_catalog_sent
        - battery_selected
        - payment_link_sent
        - dispatch_requested
        - advisor_handoff
        - out_of_coverage
        - done

        Reglas:
        - Si falta nombre: next_step = "ask_name".
        - Si falta marca, modelo o año: next_step = "ask_vehicle".
        - Si falta ciudad o ubicación: next_step = "ask_location".
        - Si ya hay nombre, vehículo completo y ubicación: next_step = "confirm_data".
        - No confirmes datos incompletos.
        - No transfieras al asesor sin confirmación.
        - Pregunta únicamente por el siguiente dato faltante.
        - No vuelvas a pedir datos ya registrados.

        Si el cliente menciona una ciudad fuera de cobertura:
        next_step = "out_of_coverage"
        should_send = true

        Respuesta:
        "Gracias por escribirnos. Actualmente atendemos Medellín y Área Metropolitana."

        Si el cliente menciona moto, motocicleta, scooter, ATV o cuatrimoto:
        next_step = "out_of_coverage"
        should_send = true

        Respuesta:
        "Gracias por escribirnos 🙌 Actualmente solo manejamos baterías para carros, camionetas y camiones."

        Si current_step es "confirm_data":
        - Si confirma datos correctos: intent = "confirm_data_correct" y next_step = "catalog_sent".
        - Si pide corregir: intent = "correct_data" y next_step = "ask_name".
        - Si no es claro: intent = "unknown" y next_step = "confirm_data".
        """
    ).strip()

