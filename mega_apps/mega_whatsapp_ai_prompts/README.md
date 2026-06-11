# Mega WhatsApp AI Prompts

Modulo base para administrar visualmente prompts de IA de WhatsApp desde Odoo.

Esta primera fase crea la estructura funcional del modulo, el modelo
`mega.whatsapp.ai.prompt`, vistas, menus, seguridad y registros iniciales
placeholder. No integra todavia la lectura dinamica con el flujo actual de
`mega_n8n_crm_connector`.

## Objetivo

Centralizar prompts de IA usados por los flujos WhatsApp para poder editarlos
desde Odoo en una fase posterior, sin modificar todavia el flujo existente que
hoy arma prompts desde codigo Python.

## Crear un prompt desde Odoo

1. Ir a CRM > WhatsApp IA > Prompts IA.
2. Crear un registro nuevo.
3. Completar nombre, codigo, tipo de flujo y tipo de prompt.
4. Escribir el texto del prompt.
5. Opcionalmente limitarlo por compania, equipo de ventas, horario o version.

Los usuarios CRM tienen lectura. El grupo `Administrador de Prompts IA WhatsApp`
puede crear, editar y eliminar.

## flow_type

- `simple`: prompt pensado para el flujo simple de captura basica.
- `advanced`: prompt pensado para el flujo avanzado actual del conector.

## prompt_type

- `main`: prompt principal del flujo.
- `after_hours`: prompt usado fuera de horario.
- `advisor_handoff`: mensajes o instrucciones para paso a asesor.
- `multimedia`: instrucciones para imagen, audio, documento u otros medios.
- `coverage`: reglas de cobertura.
- `fallback`: respuestas de respaldo o control.

## Integracion esperada en fase 2

La fase 2 deberia agregar una capa de resolucion de prompts en
`mega_n8n_crm_connector` que consulte `mega.whatsapp.ai.prompt` y devuelva el
prompt activo segun `flow_type`, `prompt_type`, codigo, compania y equipo.

La integracion debe conservar fallback al prompt actual en codigo para evitar
romper el flujo de texto. Se recomienda iniciar con `simple_main` y
`simple_after_hours`.

## Archivos detectados con prompts o logica relacionada

- `helpers/whatsapp_ai_prompt_simple.py`
- `helpers/prompts/simple/bussines_context_simple.py`
- `helpers/prompts/simple/welcome_rules_simple.py`
- `helpers/prompts/simple/vehicle_corrections_simple.py`
- `helpers/whatsapp_ai_prompt_after_hours.py`
- `helpers/whatsapp_ai_prompt.py`
- `helpers/prompts/business_context.py`
- `helpers/prompts/welcome_rules.py`
- `helpers/prompts/capture_rules.py`
- `helpers/prompts/flow_rules.py`
- `helpers/prompts/catalog_rules.py`
- `helpers/prompts/json_schema.py`
- `helpers/prompts/session_context.py`
- `helpers/prompts/tone_rules.py`
- `helpers/services/whatsapp_flow_service.py`
- `helpers/whatsapp_session_helper.py`
- `helpers/whatsapp_messages.py`
- `helpers/constants.py`
- `controllers/whatsapp_flow_controller.py`

Ver `docs/prompt_inventory.md` para el inventario detallado.

## Nota de alcance

En esta fase no se modifico `mega_n8n_crm_connector`. El modulo nuevo solo
depende de el y documenta los puntos actuales de prompts/logica IA para preparar
una migracion posterior.
