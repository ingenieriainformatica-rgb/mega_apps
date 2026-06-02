# -*- coding: utf-8 -*-

def get_whatsapp_flow_mode(env) -> str:
    Config = env["ir.config_parameter"].sudo()
    mode = (
        Config.get_param("whatsapp_flow_mode")
        or Config.get_param("whatsapp.flow_mode")
        or "advanced"
    )

    mode = (mode or "advanced").strip().lower()

    if mode not in {"simple", "advanced"}:
        return "advanced"

    return mode


def is_simple_whatsapp_flow(env) -> bool:
    return get_whatsapp_flow_mode(env) == "simple"
