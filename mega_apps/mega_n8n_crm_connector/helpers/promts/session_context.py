from textwrap import dedent


def _clean(value):
    return value or "Sin registrar"


def get_session_context(session) -> str:
    return dedent(
        f"""
        # ESTADO ACTUAL

        current_step:
        {_clean(getattr(session, "step", None))}

        current_welcome_sent:
        {getattr(session, "welcome_sent", False)}

        current_customer_name:
        {_clean(getattr(session, "customer_name", None))}

        current_vehicle_info:
        {_clean(getattr(session, "vehicle_info", None))}

        current_vehicle_brand:
        {_clean(getattr(session, "vehicle_brand", None))}

        current_vehicle_model:
        {_clean(getattr(session, "vehicle_model", None))}

        current_vehicle_year:
        {_clean(getattr(session, "vehicle_year", None))}

        current_city:
        {_clean(getattr(session, "city", None))}

        current_location:
        {_clean(getattr(session, "location", None))}

        current_plate:
        {_clean(getattr(session, "plate", None))}

        current_summary:
        {_clean(getattr(session, "conversation_summary", None))}
        """
    ).strip()
