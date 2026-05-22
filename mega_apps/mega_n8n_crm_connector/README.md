# Mega n8n CRM Connector

Modulo de Odoo 18 para conectar flujos de n8n con CRM, contactos y una atencion inicial por WhatsApp para Mega Baterias.

El proyecto esta orientado a recibir mensajes desde n8n, mantener una sesion conversacional por numero de WhatsApp, pedir los datos minimos para cotizar una bateria y entregar la conversacion a un asesor humano cuando la informacion queda confirmada.

## Que hace este modulo

- Expone endpoints JSON publicos para que n8n consulte y actualice el estado de una conversacion de WhatsApp.
- Crea y actualiza sesiones en el modelo `mega.whatsapp.session`.
- Guarda telefono, nombre del cliente, vehiculo, ubicacion, ultimo mensaje y paso actual del flujo.
- Genera instrucciones para una IA externa, normalmente llamada desde n8n.
- Aplica el resultado de la IA sobre la sesion de Odoo.
- Evita continuar conversaciones que ya fueron entregadas a asesor o finalizadas.
- Permite reabrir una nueva sesion si la sesion terminal expiro o si el cliente pide otra bateria, otro vehiculo o reiniciar.

## Dependencias

El manifiesto declara estas dependencias:

- `base`
- `crm`

Modulo:

- Nombre tecnico del addon: `mega_n8n_crm_connector`
- Version: `18.0.1.0.0`
- Categoria: `MegaTecnicentro/CrmN8n`
- Licencia: `LGPL-3`

## Estructura del codigo

```text
mega_n8n_crm_connector/
├── __manifest__.py
├── __init__.py
├── controllers/
│   ├── __init__.py
│   ├── whatsapp_flow_controller.py
│   └── n8n_partner_controller.py
├── helpers/
│   ├── __init__.py
│   ├── n8n_payload_helper.py
│   └── whatsapp_session_helper.py
├── models/
│   ├── __init__.py
│   └── mega_whatsapp_sessions.py
├── services/
│   └── whatsapp_ai_service.py
└── static/
    └── description/
        └── icon.png
```

## Modelo principal

### `mega.whatsapp.session`

Archivo: `models/mega_whatsapp_sessions.py`

Este modelo representa una sesion de atencion por WhatsApp.

Campos principales:

- `phone`: numero del cliente. Es obligatorio e indexado.
- `phone_number_id`: identificador del numero de WhatsApp usado por Meta/n8n.
- `step`: paso actual de la conversacion.
- `customer_name`: nombre capturado del cliente.
- `vehicle_info`: informacion del vehiculo.
- `location`: barrio, ciudad o ubicacion del cliente.
- `last_message`: ultimo mensaje recibido.
- `lead_id`: oportunidad CRM asociada, aunque actualmente el flujo activo no la crea automaticamente.
- `active`: indica si la sesion sigue activa.

Pasos disponibles:

- `new`
- `ask_name`
- `ask_vehicle`
- `ask_location`
- `confirm_data`
- `advisor_handoff`
- `done`

## Endpoints activos

Los endpoints activos estan en `controllers/whatsapp_flow_controller.py`, porque `controllers/__init__.py` solo importa `whatsapp_flow_controller`.

### `POST /n8n/whatsapp/session/ai-context`

Prepara el contexto que n8n debe enviar a la IA.

Entrada esperada:

```json
{
  "phone": "573001112233",
  "message": "Hola, soy Carlos y necesito bateria para un Spark",
  "phone_number_id": "123456789"
}
```

Tambien soporta formato JSON-RPC con los datos dentro de `params`.

Respuesta cuando se crea una sesion nueva:

```json
{
  "success": true,
  "should_use_ai": false,
  "should_send": true,
  "kind": "welcome",
  "reply": "Mensaje de bienvenida",
  "step": "ask_name"
}
```

Respuesta cuando la sesion ya existe y debe pasar por IA:

```json
{
  "success": true,
  "should_use_ai": true,
  "should_send": false,
  "kind": "ai_context",
  "phone": "573001112233",
  "step": "ask_vehicle",
  "customer_name": "Carlos",
  "vehicle_info": "",
  "location": "",
  "last_message": "Tengo un Spark 2018",
  "ai_instruction": "Instruccion completa para la IA"
}
```

### `POST /n8n/whatsapp/session/apply-ai`

Aplica sobre Odoo el JSON producido por la IA.

Entrada esperada:

```json
{
  "phone": "573001112233",
  "ai_result": {
    "customer_name": "Carlos",
    "vehicle_info": "Chevrolet Spark 2018",
    "location": "Laureles",
    "intent": "battery_quote",
    "confidence": 0.95,
    "next_step": "confirm_data",
    "should_send": true,
    "reply": ""
  }
}
```

Si `next_step` queda en `confirm_data`, el modulo reemplaza la respuesta por un mensaje de confirmacion con nombre, vehiculo y ubicacion.

## Flujo de WhatsApp

1. n8n recibe un mensaje entrante de WhatsApp.
2. n8n llama a `/n8n/whatsapp/session/ai-context`.
3. Si no existe sesion activa, Odoo crea una en `ask_name` y devuelve un mensaje de bienvenida.
4. Si la sesion ya existe y no esta finalizada, Odoo devuelve contexto e instrucciones para la IA.
5. n8n ejecuta la IA con la instruccion recibida.
6. n8n llama a `/n8n/whatsapp/session/apply-ai` con el resultado de la IA.
7. Odoo actualiza la sesion y responde el mensaje que debe enviarse al cliente.
8. Cuando el cliente confirma los datos, la sesion pasa a `advisor_handoff`.

## Logica de sesion

La logica central esta en `helpers/whatsapp_session_helper.py`.

Funciones importantes:

- `get_or_create_session`: busca una sesion activa por telefono o crea una nueva.
- `get_ai_instruction`: construye el prompt/instruccion que n8n debe pasar a la IA.
- `parse_ai_result`: convierte el resultado de IA a diccionario Python.
- `build_ai_session_update`: decide el siguiente paso y los valores a guardar.
- `resolve_confirmation_from_ai`: interpreta respuestas de confirmacion como `si`, `sí`, `ok`, `no` o `corregir`.
- `terminal_session_expired`: permite reabrir sesiones terminales despues de 8 dias.
- `message_requests_new_session`: detecta frases como `otra bateria`, `otro carro` o `reiniciar`.

## Instruccion para la IA

La IA debe devolver solo JSON valido con esta estructura:

```json
{
  "customer_name": "",
  "vehicle_info": "",
  "location": "",
  "intent": "",
  "confidence": 0,
  "next_step": "",
  "should_send": true,
  "reply": ""
}
```

Reglas principales:

- No inventar datos.
- Extraer nombre, vehiculo y ubicacion cuando aparezcan.
- Usar `battery_quote` como intent cuando el cliente busca una bateria.
- No dar precios.
- No confirmar disponibilidad.
- Responder corto y natural para WhatsApp.
- Pasar a `advisor_handoff` si el cliente confirma o pide asesor humano.

## Archivos heredados o no activos

### `controllers/n8n_partner_controller.py`

Este archivo contiene una version anterior o alternativa del controlador. Actualmente no se importa desde `controllers/__init__.py`, por lo tanto sus rutas no quedan activas al cargar el modulo.

Incluye endpoints que podrian recuperarse si se vuelve a importar:

- `POST /n8n/partner/check-email`
- `POST /n8n/crm/create-lead`
- `POST /n8n/whatsapp/session/process`
- `POST /n8n/whatsapp/session/ai-context`
- `POST /n8n/whatsapp/session/apply-ai`

Tambien contiene una validacion por token con el parametro de sistema:

```text
mega_n8n_crm_connector.n8n_token
```

Si este controlador se reactiva, hay que tener cuidado porque define rutas duplicadas para `ai-context` y `apply-ai`.

### `services/whatsapp_ai_service.py`

Actualmente solo contiene una funcion auxiliar `_get_n8n_payload`, similar a la de `helpers/n8n_payload_helper.py`. No se ve usada por el flujo activo.

## Observaciones tecnicas

- Los endpoints activos usan `auth="public"` y `csrf=False`. Esto facilita la integracion con n8n, pero conviene agregar autenticacion por token si el endpoint queda expuesto a internet.
- `n8n_partner_controller.py` tiene logica duplicada frente a los helpers actuales. Lo ideal seria eliminarlo si ya no se usa o reactivarlo solo despues de unificar rutas.
- `lead_id` existe en el modelo de sesion, pero el flujo activo no crea oportunidades CRM automaticamente.
- `helpers/n8n_payload_helper.py` y `services/whatsapp_ai_service.py` tienen funciones de payload muy parecidas. Conviene dejar una sola fuente.
- La reapertura automatica de sesiones terminales ocurre despues de 8 dias o cuando el mensaje contiene una intencion de nueva cotizacion.

## Ejemplo de integracion en n8n

Flujo recomendado:

1. Webhook de WhatsApp recibe `phone`, `message` y `phone_number_id`.
2. HTTP Request a Odoo: `/n8n/whatsapp/session/ai-context`.
3. Si `should_send=true`, n8n envia `reply` al cliente y termina.
4. Si `should_use_ai=true`, n8n llama al modelo de IA con `ai_instruction`.
5. HTTP Request a Odoo: `/n8n/whatsapp/session/apply-ai`.
6. Si `should_send=true`, n8n envia `reply` al cliente.
7. Si `step=advisor_handoff`, n8n puede notificar a un asesor humano o enrutar la conversacion.

## Resumen

Este addon convierte Odoo en el backend de estado para un asistente de WhatsApp operado desde n8n. Su responsabilidad principal no es vender directamente ni calcular precios, sino capturar datos basicos del cliente y su vehiculo, validar la informacion y dejar lista la conversacion para que un asesor de Mega Baterias continue la atencion.
