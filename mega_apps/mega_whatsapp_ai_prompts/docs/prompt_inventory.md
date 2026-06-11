# Inventario de prompts actuales

Este inventario fue levantado en modo solo lectura sobre `mega_n8n_crm_connector`.
En esta fase no se modifico ningun archivo de ese modulo.

| Archivo detectado | Funcion o variable | Tipo probable | Observaciones | Recomendacion futura |
|---|---|---|---|---|
| `helpers/whatsapp_ai_prompt_simple.py` | `get_simple_ai_instruction(session, message)` | simple/main | Ensambla el prompt principal del flujo simple con contexto de negocio, reglas de bienvenida, correcciones de vehiculo, schema JSON y estado de sesion. | Migrar como prompt compuesto o dividir en secciones reutilizables. |
| `helpers/prompts/simple/bussines_context_simple.py` | `get_business_context_simple()` | simple/main | Contexto de negocio simple. El nombre del archivo tiene typo `bussines`. | Migrar a prompt base simple o componente de contexto. |
| `helpers/prompts/simple/welcome_rules_simple.py` | `get_welcome_rules_simple()` | simple/main | Reglas de bienvenida para el flujo simple. | Migrar como componente asociado a `simple_main`. |
| `helpers/prompts/simple/vehicle_corrections_simple.py` | `get_vehicle_corrections_simple()` | simple/main, simple/after_hours | Reglas de correccion/extraccion de vehiculo usadas por simple y fuera de horario. | Migrar como bloque reusable. |
| `helpers/whatsapp_ai_prompt_after_hours.py` | `get_after_hours_ai_instruction(session, message)` | advanced/after_hours, simple/after_hours | Prompt de fuera de horario compartido antes de elegir simple/advanced cuando aplica horario. | Crear prompt `after_hours` comun o parametrizado por flujo. |
| `helpers/whatsapp_ai_prompt.py` | `get_ai_instruction(session, message)` | advanced/main | Ensambla el prompt avanzado desde multiples helpers de `helpers/prompts`. | Migrar como prompt avanzado principal compuesto. |
| `helpers/prompts/business_context.py` | `get_business_context()` | advanced/main | Contexto de negocio avanzado. | Migrar como componente de contexto avanzado. |
| `helpers/prompts/welcome_rules.py` | `get_welcome_rules()` | advanced/main | Reglas de bienvenida avanzadas. | Migrar como componente. |
| `helpers/prompts/capture_rules.py` | `get_capture_rules()` | advanced/main | Reglas de captura progresiva. | Migrar como componente. |
| `helpers/prompts/flow_rules.py` | `get_flow_rules()` | advanced/main, coverage | Reglas de estados, cobertura y transiciones. | Separar reglas de flujo y cobertura si se quiere administracion fina. |
| `helpers/prompts/catalog_rules.py` | `get_catalog_rules()` | advanced/main | Reglas de catalogo. | Mantener fuera de esta primera migracion si no se va a tocar catalogo. |
| `helpers/prompts/json_schema.py` | `get_json_schema()` | advanced/main | Schema JSON esperado para respuesta de IA. | Migrar con cuidado; es contrato tecnico. |
| `helpers/prompts/session_context.py` | `get_session_context(session, message)` | advanced/main | Inyecta estado actual de la sesion y mensaje del cliente. | Mantener dinamico en codigo y combinar con prompt editable. |
| `helpers/prompts/tone_rules.py` | `get_tone_rules()` | advanced/main | Reglas de tono. | Migrar como componente editable. |
| `helpers/services/whatsapp_flow_service.py` | `build_ai_context_response()` | otro | Decide si usar prompt after-hours, simple o avanzado y devuelve `ai_instruction` a n8n. | En fase 2, leer prompt activo desde `mega.whatsapp.ai.prompt` aqui o en un servicio dedicado. |
| `helpers/whatsapp_session_helper.py` | `build_simple_ai_session_update()`, `build_after_hours_ai_session_update()`, cobertura | coverage, fallback, otro | No arma el prompt principal, pero interpreta respuesta IA, aplica cobertura y arma mensajes fallback/control. | No migrar completo como prompt; documentar reglas de negocio separadas. |
| `helpers/whatsapp_messages.py` | mensajes de bienvenida, confirmacion, fuera de cobertura, handoff | fallback, coverage, advisor_handoff | Textos de respuesta no necesariamente enviados como prompt IA. | Evaluar despues si deben administrarse desde Odoo como plantillas, no como prompts. |
| `helpers/constants.py` | listas de cobertura, estados, keywords | coverage, otro | Contiene listas y constantes usadas por prompts/flujo. | Mantener como reglas tecnicas hasta disenar administracion de cobertura. |
| `controllers/whatsapp_flow_controller.py` | rutas `/n8n/whatsapp/session/ai-context` y `/apply-ai` | otro | Publica endpoints; no arma prompts directamente. | No migrar; solo integrar indirectamente via servicio. |

## Recomendacion para fase 2

Agregar un servicio de resolucion de prompts que busque el registro activo por
`code`, `flow_type`, `prompt_type`, `company_id` y `team_id`, con fallback al
prompt actual quemado en codigo. La primera integracion deberia limitarse a
`simple_main` y `simple_after_hours` para no afectar catalogo, Wompi ni flujo
avanzado.
