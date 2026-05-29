from textwrap import dedent


def get_json_schema() -> str:
    return dedent(
        """
        # FORMATO OBLIGATORIO

        Responde SOLO JSON válido.
        NO uses markdown.
        NO expliques.
        NO agregues texto adicional.
        assistant_message y reply deben tener exactamente el mismo texto.

        # JSON OBLIGATORIO

        {
          "intent": "progressive_data_capture",
          "customer_name": null,
          "vehicle_brand": null,
          "vehicle_model": null,
          "vehicle_year": null,
          "vehicle_type": null,
          "vehicle_info": null,
          "city": null,
          "neighborhood": null,
          "location": null,
          "plate": null,
          "battery_request": false,
          "relevant_data": null,
          "detected_fields": [],
          "missing_required_fields": [],
          "next_required_field": null,
          "can_advance": false,
          "assistant_message": "",
          "conversation_summary": "",
          "selected_catalog_option": 0,
          "customer_leaves_old_battery": true,
          "confidence": 0,
          "lead_quality": "",
          "is_emergency": false,
          "next_step": "",
          "should_send": true,
          "reply": ""
        }

        Durante captura inicial intent debe ser "progressive_data_capture".
        Solo en pasos de catálogo usa los intents específicos de catálogo.
        """
    ).strip()
