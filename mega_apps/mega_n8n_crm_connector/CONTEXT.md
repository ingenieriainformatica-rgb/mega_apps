# Contexto del proyecto: mega_n8n_crm_connector

## Resumen ejecutivo

`mega_n8n_crm_connector` es un addon de Odoo 18 para conectar flujos de n8n con CRM, contactos y una atencion automatizada por WhatsApp para Mega Baterias.

Su objetivo principal es usar Odoo como backend de estado para conversaciones recibidas desde WhatsApp/n8n. El modulo guarda una sesion por numero de WhatsApp, pide datos minimos del cliente, interpreta resultados de una IA externa, crea o actualiza leads CRM, consulta opciones de baterias compatibles y deja la conversacion lista para seguimiento humano.

El modulo no es el bot completo por si solo. Odoo mantiene estado, reglas de negocio y CRM. n8n recibe mensajes, llama a Odoo, ejecuta la IA cuando Odoo lo solicita y envia al cliente las respuestas retornadas por Odoo.

## Datos del addon

- Nombre tecnico: `mega_n8n_crm_connector`
- Version: `18.0.1.0.0`
- Categoria: `MegaTecnicentro/CrmN8n`
- Autor: `Jorge Alberto Quiroz Sierra`
- Website: `https://mega.realnet.com.co/`
- Licencia: `LGPL-3`
- Dependencias declaradas: `base`, `crm`
- Tipo: addon no marcado como aplicacion (`application=False`)

## Estructura real del proyecto

```text
mega_n8n_crm_connector/
├── __init__.py
├── __manifest__.py
├── README.md
├── CONTEXT.md
├── controllers/
│   ├── __init__.py
│   ├── whatsapp_flow_controller.py
│   └── n8n_partner_controller.py
├── helpers/
│   ├── __init__.py
│   ├── constants.py
│   ├── n8n_payload_helper.py
│   ├── whatsapp_ai_prompt.py
│   ├── whatsapp_catalog_helper.py
│   ├── whatsapp_chatter_helper.py
│   ├── whatsapp_crm_helper.py
│   ├── whatsapp_messages.py
│   ├── whatsapp_session_helper.py
│   ├── whatsapp_vehicle_helper.py
│   ├── wompi_payment_helper.py
│   └── services/
│       ├── __init__.py
│       └── whatsapp_flow_service.py
├── models/
│   ├── __init__.py
│   ├── crm_leads.py
│   └── mega_whatsapp_sessions.py
├── services/
│   └── whatsapp_ai_service.py
└── static/
    └── description/
        └── icon.png
```

Hay carpetas `__pycache__` dentro del addon. Son artefactos compilados de Python y no hacen parte del diseno funcional.

## Carga del modulo

`__init__.py` importa:

- `controllers`
- `models`
- `helpers`
- `services`

`controllers/__init__.py` solo importa `whatsapp_flow_controller`. Por eso los endpoints activos del flujo actual son los definidos en `controllers/whatsapp_flow_controller.py`.

`models/__init__.py` importa:

- `mega_whatsapp_sessions`
- `crm_leads`

`helpers/__init__.py` esta vacio. Los helpers se importan directamente desde los servicios y controladores.

## Endpoints activos

Los endpoints activos estan en `controllers/whatsapp_flow_controller.py`.

Todos son rutas JSON publicas:

- `auth="public"`
- `csrf=False`
- `methods=["POST"]`
- `website=False`

### POST `/n8n/whatsapp/session/ai-context`

Entrada principal desde n8n cuando llega un mensaje de WhatsApp.

Responsabilidad:

- Leer el payload recibido.
- Validar telefono.
- Buscar o crear una sesion activa.
- Si la sesion es nueva, devolver mensaje de bienvenida sin usar IA.
- Si la sesion ya existe y no esta en estado terminal, devolver contexto e instruccion para IA.
- Si la sesion esta en estado terminal, indicar que no debe usarse IA ni enviarse respuesta automatica.

Payload esperado:

```json
{
  "phone": "573001112233",
  "message": "Hola, necesito una bateria para un Spark 2018",
  "phone_number_id": "1115813888271835"
}
```

Tambien soporta JSON-RPC con datos dentro de `params`.

Respuesta cuando crea sesion:

```json
{
  "success": true,
  "should_use_ai": false,
  "should_send": true,
  "kind": "welcome",
  "phone": "573001112233",
  "step": "ask_name",
  "reply": "mensaje de bienvenida",
  "session": {}
}
```

Respuesta cuando debe pasar por IA:

```json
{
  "success": true,
  "should_use_ai": true,
  "should_send": false,
  "kind": "ai_context",
  "phone": "573001112233",
  "phone_number_id": "1115813888271835",
  "step": "ask_vehicle",
  "customer_name": "Carlos",
  "vehicle_info": "",
  "location": "",
  "last_message": "Tengo un Spark 2018",
  "ai_instruction": "prompt completo para la IA",
  "session": {}
}
```

### POST `/n8n/whatsapp/session/apply-ai`

Segundo paso del flujo. n8n llama este endpoint despues de ejecutar la IA.

Responsabilidad:

- Leer `phone` y `ai_result`.
- Buscar la sesion activa.
- Interpretar el JSON de IA.
- Actualizar la sesion.
- Crear o actualizar el lead CRM.
- Consultar catalogo cuando el flujo llega a `catalog_sent`.
- Construir el mensaje final que n8n debe enviar.
- Registrar conversacion en el chatter del lead.

Payload esperado:

```json
{
  "phone": "573001112233",
  "ai_result": {
    "customer_name": "Carlos",
    "vehicle_info": "Chevrolet Spark 2018",
    "vehicle_brand": "Chevrolet",
    "vehicle_model": "Spark",
    "vehicle_year": "2018",
    "location": "Laureles",
    "conversation_summary": "Cliente busca bateria para Spark 2018 en Laureles.",
    "intent": "battery_quote",
    "confidence": 0.95,
    "lead_quality": "high",
    "is_emergency": false,
    "next_step": "confirm_data",
    "should_send": true,
    "reply": ""
  }
}
```

Respuesta tipica:

```json
{
  "success": true,
  "step": "confirm_data",
  "should_send": true,
  "reply": "mensaje para enviar por WhatsApp",
  "session": {},
  "lead_id": 123
}
```

### POST `/n8n/whatsapp/session/log-message`

Endpoint para registrar mensajes entrantes cuando la sesion ya esta en estado terminal y no debe seguir pasando por IA.

Responsabilidad:

- Validar telefono.
- Buscar sesion activa.
- Confirmar que el paso sea terminal.
- Registrar el mensaje del cliente en el lead vinculado a esa sesion.
- Evitar duplicados usando `message_id` contra `last_inbound_message_id`.

Payload esperado:

```json
{
  "phone": "573001112233",
  "message": "Gracias, quedo atento",
  "message_id": "wamid.xxx"
}
```

## Controlador heredado no activo

`controllers/n8n_partner_controller.py` contiene una version anterior o alternativa del flujo. Actualmente no se carga porque `controllers/__init__.py` no lo importa.

Rutas incluidas ahi, pero no activas mientras no se importe:

- `/n8n/partner/check-email`
- `/n8n/crm/create-lead`
- `/n8n/whatsapp/session/process`
- `/n8n/whatsapp/session/ai-context`
- `/n8n/whatsapp/session/apply-ai`

Este controlador tiene logica duplicada de sesion, prompt y aplicacion de IA. Tambien incluye validacion por token con:

```text
mega_n8n_crm_connector.n8n_token
```

Si se reactiva, hay que unificarlo primero porque define rutas duplicadas de `ai-context` y `apply-ai`.

## Modelo principal: mega.whatsapp.session

Archivo: `models/mega_whatsapp_sessions.py`

Modelo Odoo:

```python
_name = "mega.whatsapp.session"
_description = "Sesion WhatsApp n8n"
_order = "write_date desc"
```

Representa una conversacion de WhatsApp asociada a un telefono.

Campos principales:

- `phone`: telefono del cliente. Obligatorio e indexado.
- `phone_number_id`: identificador de la linea de WhatsApp/Meta usada por n8n.
- `step`: estado actual del flujo.
- `customer_name`: nombre capturado.
- `vehicle_info`: texto legible del vehiculo.
- `location`: ubicacion, barrio o municipio.
- `last_message`: ultimo mensaje entrante.
- `lead_id`: lead CRM asociado.
- `active`: indica si la sesion sigue activa.
- `last_inbound_message_id`: ultimo id de mensaje entrante registrado, usado para evitar duplicados.
- `conversation_summary`: resumen corto del contexto conversacional generado por IA.
- `selected_battery_option_id`: opcion de bateria seleccionada.
- `customer_leaves_old_battery`: indica si el cliente entrega bateria usada. Por defecto `True`.
- `selected_battery_price`: precio de bateria seleccionado.
- `wompi_payment_link_id`: id de link de Wompi.
- `wompi_payment_url`: URL de pago de Wompi.

Estados definidos en el modelo:

- `new`
- `ask_name`
- `ask_vehicle`
- `ask_location`
- `confirm_data`
- `out_of_coverage`
- `catalog_sent`
- `more_options_sent`
- `battery_selected`
- `dispatch_requested`
- `payment_link_sent`
- `advisor_handoff`
- `done`

Regla de unicidad:

El metodo `init()` elimina una constraint antigua y crea un indice unico parcial:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS mega_whatsapp_session_unique_active_phone_idx
ON mega_whatsapp_session (phone)
WHERE active IS TRUE
```

Esto permite multiples sesiones historicas por telefono, pero solo una activa por numero.

## Extension de CRM

Archivo: `models/crm_leads.py`

Extiende `crm.lead`.

Responsabilidades:

- Detectar si un lead esta en estado terminal.
- Considerar terminal un lead inactivo, ganado o en etapa plegada (`fold`).
- Evitar que un lead de WhatsApp ya cerrado vuelva a una etapa abierta si tiene una sesion cerrada en `done`.
- Cerrar sesiones WhatsApp activas cuando el lead llega a estado terminal.
- Publicar una nota en el chatter cuando una sesion se cierra automaticamente.

Regla importante:

Si un lead ya tiene una sesion WhatsApp cerrada, no debe reabrirse para una nueva conversacion. Si el cliente vuelve a escribir, el sistema debe crear nueva sesion y nuevo lead.

## Flujo funcional principal

1. WhatsApp recibe mensaje del cliente.
2. n8n normaliza datos y llama `/n8n/whatsapp/session/ai-context`.
3. Odoo busca una sesion activa por telefono.
4. Si no existe, Odoo crea sesion en `ask_name` y devuelve bienvenida.
5. Si existe y no es terminal, Odoo devuelve contexto y prompt para IA.
6. n8n ejecuta la IA con `ai_instruction`.
7. n8n llama `/n8n/whatsapp/session/apply-ai`.
8. Odoo interpreta el resultado de IA y actualiza la sesion.
9. Odoo crea o actualiza contacto y lead CRM cuando ya hay nombre.
10. Si los datos llegan a confirmacion, Odoo envia mensaje de confirmacion.
11. Si el cliente confirma, el flujo pasa a `catalog_sent`.
12. Odoo consulta catalogo de baterias para el lead.
13. Si hay opcion recomendada, Odoo devuelve recomendacion.
14. Si no hay opciones, Odoo devuelve mensaje para revision manual y puede pasar a asesor.
15. Las conversaciones se registran en el chatter del lead.
16. Si el lead se cierra, se cierra la sesion vinculada.

## Estados del flujo y significado

- `ask_name`: falta nombre del cliente.
- `ask_vehicle`: ya hay nombre, falta marca/modelo/ano del vehiculo.
- `ask_location`: ya hay vehiculo, falta ubicacion.
- `confirm_data`: ya hay nombre, vehiculo y ubicacion; el cliente debe confirmar.
- `out_of_coverage`: cliente esta fuera de cobertura o pide producto no atendido.
- `catalog_sent`: se envio o se esta por enviar opcion recomendada de bateria.
- `more_options_sent`: cliente pidio mas opciones del catalogo.
- `battery_selected`: cliente eligio una opcion de bateria.
- `dispatch_requested`: estado reservado para despacho.
- `payment_link_sent`: estado reservado para pago.
- `advisor_handoff`: conversacion entregada a asesor humano.
- `done`: sesion cerrada historicamente.

Estados terminales segun `helpers/constants.py`:

- `out_of_coverage`
- `advisor_handoff`
- `dispatch_requested`
- `done`

## Reapertura de sesiones

La logica esta en `helpers/whatsapp_session_helper.py`.

Cuando existe una sesion activa en estado terminal, `get_or_create_session()` decide si debe cerrarla y crear una nueva.

Crea nueva sesion si:

- La sesion terminal expiro.
- El mensaje indica nueva cotizacion o reinicio.

Tiempo de expiracion:

```python
SESSION_REOPEN_MINUTES = 60 * 24 * 8
```

Equivale a 8 dias.

Palabras clave de nueva sesion:

- `otra batería`
- `otra bateria`
- `nueva batería`
- `nueva bateria`
- `nueva cotización`
- `nueva cotizacion`
- `otro carro`
- `otro vehículo`
- `otro vehiculo`
- `reiniciar`
- `empezar de nuevo`

Cuando se cierra una sesion, se escribe:

```python
{"active": False, "step": "done"}
```

## Prompt de IA

Archivo: `helpers/whatsapp_ai_prompt.py`

`get_ai_instruction(session, message)` construye el prompt completo que n8n debe enviar al modelo de IA.

La IA debe actuar como asesor comercial de Mega Baterias y responder solo JSON valido. No debe mencionar IA, bot ni automatizacion.

Reglas fuertes:

- No inventar informacion.
- No dar precios.
- No confirmar disponibilidad.
- No prometer cobertura.
- No vender productos fuera del alcance.
- No actuar como tecnico especializado.
- No hacer multiples preguntas principales al tiempo.
- Mantener tono natural de WhatsApp.
- Maximo 280 caracteres para respuestas al cliente.
- Transferir a asesor solo cuando corresponda.

JSON obligatorio:

```json
{
  "customer_name": "",
  "vehicle_info": "",
  "vehicle_brand": "",
  "vehicle_model": "",
  "vehicle_year": "",
  "location": "",
  "conversation_summary": "",
  "intent": "battery_quote",
  "confidence": 0,
  "lead_quality": "",
  "is_emergency": false,
  "next_step": "",
  "should_send": true,
  "reply": ""
}
```

La IA tambien debe detectar:

- Emergencias: `urgente`, `varado`, `no prende`, `batería descargada`, etc.
- Calidad del lead: `low`, `medium`, `high`.
- Solicitudes fuera de cobertura.
- Motos y marcas de moto, que deben ir a `out_of_coverage`.
- Correcciones obvias de escritura en marcas, modelos y nombres.

## Manejo de cobertura

La cobertura esta definida en `helpers/constants.py`.

Cobertura aceptada:

- Medellin
- Bello
- Itagui
- Envigado
- Sabaneta
- La Estrella
- Caldas
- Copacabana
- Girardota
- Barbosa

Ubicaciones marcadas como fuera de cobertura:

- Bogota
- Cali
- Barranquilla
- Cartagena
- Pereira
- Manizales
- Bucaramanga

`helpers/whatsapp_session_helper.py` tiene:

- `normalize_text()`
- `is_out_of_coverage()`

Si la ubicacion contiene un lugar permitido, no se marca como fuera de cobertura. Si contiene uno negado y no contiene lugar permitido, pasa a `out_of_coverage`.

## Creacion y actualizacion de CRM

Archivo: `helpers/whatsapp_crm_helper.py`

Funcion principal:

```python
create_or_update_lead_from_session(env, session, ai_result=None)
```

Reglas:

- No crea lead si no hay nombre del cliente.
- Busca o crea contacto por telefono.
- Normaliza telefono dejando solo digitos.
- Si encuentra contacto por `phone` o `mobile`, lo reutiliza.
- Si el contacto encontrado tiene nombre generico que empieza por `whatsapp`, lo reemplaza por el nombre real.
- Si la sesion ya tiene `lead_id`, actualiza datos variables.
- Si no tiene `lead_id`, crea una oportunidad.

Datos comunes del lead:

- `partner_id`
- `contact_name`
- `phone`
- `description`
- `type="opportunity"`

Al crear lead nuevo:

- `name`: usa el formato `{line_label} - WhatsApp - {customer_name}`.
- `crm_fecha_instalacion`: se asigna si el campo existe.
- `team_id`: se asigna si existe equipo con nombre configurado.
- `user_id`: se asigna si existe usuario configurado.
- `website`: se asigna si el campo existe.

Configuracion de linea WhatsApp:

```python
WHATSAPP_LINE_CONFIGS = {
    "1115813888271835": {
        "label": "Mega Baterías",
        "website": "https://megabaterias.co",
        "team_name": "Baterías",
        "user_name": "TIENDA DIGITAL",
    },
}
```

Si no hay configuracion para `phone_number_id`, usa `DEFAULT_WHATSAPP_LINE_CONFIG`.

## Vehiculo y campos personalizados del lead

Archivo: `helpers/whatsapp_vehicle_helper.py`

Campos configurados en `helpers/constants.py`:

```python
LEAD_BRAND_FIELD = "brand_id"
LEAD_MODEL_FIELD = "modelo_id"
LEAD_YEAR_FIELD = "year_vehicule_id"
```

El helper busca:

- Marca en `fleet.vehicle.model.brand`.
- Modelo en `fleet.vehicle.model`.
- Ano segun el tipo del campo `year_vehicule_id` en `crm.lead`.

`build_vehicle_lead_values()` toma datos de `ai_result`:

- `vehicle_brand`
- `vehicle_model`
- `vehicle_year`

Y los convierte en valores escribibles para el lead si los campos existen.

`build_vehicle_info_from_ai()` construye un texto legible combinando `vehicle_info`, marca, modelo y ano, evitando duplicar datos ya presentes.

## Catalogo de baterias

Archivo: `helpers/whatsapp_catalog_helper.py`

Depende de modelos externos al addon:

- `mega.battery.application`
- `mega.battery.application.option`

Funcion de busqueda:

```python
find_battery_options_for_lead(env, lead, limit=3)
```

Requisitos para buscar:

- Lead existente.
- Marca (`brand_id`) en el lead.
- Modelo (`modelo_id`) en el lead.
- Ano (`year_vehicule_id`) resoluble como entero.

Busca aplicaciones activas por:

- `brand_id`
- `model_id`
- Rango `year_from` / `year_to`

Luego toma `option_ids` y las ordena priorizando:

- Opciones con precio.
- Opciones recomendadas por WhatsApp si el campo existe.
- Linea que contenga `gold`.
- Numero de opcion.
- Mayor precio.

Mensajes construidos:

- `build_recommended_battery_message_for_lead()`: envia una opcion recomendada.
- `build_more_battery_options_message_for_lead()`: envia hasta tres opciones.
- `build_battery_catalog_message_for_lead()`: envia catalogo o mensaje de revision manual si no hay coincidencias.

Reglas comerciales en mensajes:

- El precio aplica entregando la bateria usada.
- Si el cliente conserva la bateria usada, se adicionan $40.000.
- La disponibilidad final debe confirmarla un asesor.

## Mensajes de WhatsApp

Archivo: `helpers/whatsapp_messages.py`

Contiene plantillas aleatorias para:

- Bienvenida.
- Confirmacion de datos.
- Entrega a asesor.
- Fuera de cobertura.
- Bateria seleccionada.

Los saludos dependen de la hora de Colombia (`America/Bogota`):

- 5:00 a 11:59: `buenos días`
- 12:00 a 18:59: `buenas tardes`
- Resto: `buenas noches`

Nota tecnica:

`helpers/whatsapp_session_helper.py` tambien contiene funciones antiguas `get_colombia_greeting()` y `get_welcome_message()`, pero el flujo activo importa los mensajes desde `helpers/whatsapp_messages.py`.

## Registro en chatter

Archivo: `helpers/whatsapp_chatter_helper.py`

Funciones principales:

- `log_whatsapp_conversation_on_lead(lead, customer_message, bot_reply)`
- `log_customer_message_on_lead_from_session(session, message, message_id=None)`
- `post_whatsapp_note_on_lead(lead, title, message)`
- `post_whatsapp_message_on_lead(lead, title, message)`

Los mensajes se publican como notas internas (`mail.mt_note`) en el chatter del lead. Se usa `Markup` y `escape` para evitar HTML inseguro.

`log_customer_message_on_lead_from_session()` evita duplicados si `message_id` coincide con `last_inbound_message_id` de la sesion.

## Wompi

Archivo: `helpers/wompi_payment_helper.py`

Funcion:

```python
create_wompi_payment_link(private_key, name, description, amount, single_use=True, collect_shipping=False)
```

Endpoint usado:

```text
https://production.wompi.co/v1/payment_links
```

Checkout:

```text
https://checkout.wompi.co/l/{link_id}
```

Responsabilidad:

- Validar llave privada.
- Validar monto mayor a cero.
- Convertir COP a centavos.
- Crear link de pago con Wompi.
- Retornar `payment_link_id` y `payment_url`.

Estado actual:

Wompi ya esta integrado en el flujo de aceptacion de bateria recomendada.

Cuando la sesion esta en `catalog_sent` y el cliente acepta la bateria recomendada, el flujo pasa por `payment_link_sent`, crea el link de pago y finalmente escribe la sesion en `dispatch_requested`.

El servicio busca la llave privada de Wompi en parametros de sistema y, como respaldo, en variables de entorno.

Parametros de sistema soportados, en orden de prioridad:

- `mega_n8n_crm_connector.wompi_private_key`
- `mega_n8n_crm_connector.wompi_private_key_prod`
- `mega_n8n_crm_connector.wompi_private_key_production`
- `wompi.private_key_mega`
- `wompi.private_key`
- `wompi.private_key_mega_prod`
- `wompi.private_key_mega_production`
- `wompi.private_key_prod`
- `wompi.private_key_production`
- `wompi.private_key_mega_test`
- `wompi.private_key_test`

Variables de entorno soportadas:

- `WOMPI_PRIVATE_KEY`
- `WOMPI_PRIVATE_KEY_PROD`
- `WOMPI_PRIVATE_KEY_PRODUCTION`
- `WOMPI_PRV_KEY`

En esta base se confirmo que existen parametros Wompi reales:

- `wompi.private_key`
- `wompi.private_key_mega`
- `wompi.private_key_mega_test`
- `wompi.private_key_test`

Importante: el fallo inicial del link Wompi ocurrio porque el codigo solo buscaba `mega_n8n_crm_connector.wompi_private_key`, pero las llaves ya estaban guardadas en Odoo con nombres `wompi.*`. El log exacto visto fue:

```text
Cannot create Wompi link: private key is not configured
```

Antes de asumir que Wompi fallo, revisar:

1. Que el parametro de sistema exista con uno de los nombres soportados.
2. Que la sesion tenga `selected_battery_option_id`.
3. Que la opcion tenga precio valido (`sale_price`, `min_sale_price` o `max_sale_price`).
4. Que Wompi retorne `payment_link_id` y `payment_url`.

Si Wompi falla, el flujo no se rompe. La sesion pasa a `advisor_handoff` y se responde al cliente con un fallback indicando que un asesor continuara.

Mensaje exitoso esperado:

```text
Perfecto {nombre} 👍

Ya dejamos registrada tu solicitud:

🔋 Línea: {linea}
📌 Referencia: {referencia}
💰 Valor final: ${valor_final} COP

{nota_bateria_usada}

Puedes realizar el pago seguro aquí 👇

{payment_url}

Una vez confirmado el pago, un asesor de Mega Baterías continuará contigo para validar disponibilidad y coordinar el despacho. 🚗🔋
```

Recargo por conservar la bateria usada:

```python
OLD_BATTERY_SURCHARGE = 40000
```

## Payload n8n

Archivo: `helpers/n8n_payload_helper.py`

`get_n8n_payload()` soporta dos formatos:

JSON-RPC:

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "phone": "573001112233"
  }
}
```

JSON directo:

```json
{
  "phone": "573001112233"
}
```

Si existe `params` y es diccionario, retorna `params`. En caso contrario retorna el payload completo.

## Servicio de flujo activo

Archivo: `helpers/services/whatsapp_flow_service.py`

Funciones principales:

- `build_ai_context_response()`
- `apply_ai_to_whatsapp_session()`
- `log_terminal_whatsapp_message()`

Aunque las funciones reciben un primer parametro llamado `self`, realmente el controlador les pasa `request.env`. Dentro del servicio se usa `request.env` directamente. Funciona, pero el nombre del parametro puede confundir.

`apply_ai_to_whatsapp_session()` hace el trabajo mas importante del modulo:

1. Lee payload.
2. Parse `ai_result`.
3. Busca sesion activa.
4. Evita responder si esta en `advisor_handoff`.
5. Calcula actualizacion con `build_ai_session_update()`.
6. Escribe en sesion.
7. Crea o actualiza lead.
8. Si corresponde, arma respuesta de catalogo.
9. Si corresponde, guarda la bateria recomendada en la sesion.
10. Si el cliente acepta la bateria recomendada, crea link Wompi.
11. Si corresponde, arma confirmacion.
12. Registra conversacion en chatter.
13. Evita devolver `should_send=True` con `reply` vacio.
14. Devuelve respuesta para n8n.

## Reglas de confirmacion

Constantes en `helpers/constants.py`:

```python
CONFIRMATION_YES = {"si", "sí", "s", "correcto", "ok", "listo", "confirmo"}
CONFIRMATION_NO = {"no", "n", "incorrecto", "corregir"}
```

En el flujo actual, cuando la sesion esta en `confirm_data`:

- Si el cliente confirma de forma natural, el siguiente paso es `catalog_sent`.
- Si el cliente pide corregir algun dato, limpia nombre, vehiculo y ubicacion, y vuelve a `ask_name`.
- Si no responde claramente, mantiene `confirm_data` y pide aclarar si los datos estan correctos o si quiere corregir algo.

Ya no se fuerza el texto "Responde Si o No". El mensaje ahora pregunta de forma mas natural, por ejemplo:

```text
¿Está todo correcto o quieres que ajustemos algún dato?
```

O:

```text
Si todo está bien, seguimos con las opciones de batería. Si algo cambió, cuéntame qué dato corregimos.
```

Odoo interpreta respuestas naturales sin depender completamente de la IA.

Ejemplos que avanzan a `catalog_sent`:

- `si`
- `todo bien`
- `así está bien`
- `está perfecto`
- `dale`
- `avancemos`
- `continúa`

Ejemplos que vuelven a correccion:

- `no está bien`
- `corrige la ubicación`
- `me equivoqué`
- `el carro es otro`
- `quiero corregir el vehículo`

La IA tambien puede devolver:

- `intent = "confirm_data_correct"`
- `intent = "correct_data"`
- `intent = "unknown"`

Esto es importante porque el README antiguo indicaba que la confirmacion pasaba directo a `advisor_handoff`, pero el codigo actual la lleva primero a catalogo.

## Flujo de aceptacion de bateria recomendada

Este flujo solo se ejecuta cuando:

```python
session.step == "catalog_sent"
```

La IA no calcula precios ni genera links. Solo interpreta intencion.

Intenciones esperadas:

- `accept_recommended_battery`
- `ask_price_without_old_battery`
- `request_more_options`
- `request_advisor`
- `unknown`

Campos esperados en `ai_result`:

```json
{
  "intent": "accept_recommended_battery",
  "customer_leaves_old_battery": true
}
```

Comportamiento:

- `accept_recommended_battery`: pasa a `payment_link_sent` y el servicio crea link Wompi.
- `ask_price_without_old_battery`: mantiene `catalog_sent`, calcula el valor con recargo y lo informa.
- `request_more_options`: pasa a `more_options_sent`.
- `request_advisor`: pasa a `advisor_handoff`.

Si la IA no interpreta bien, Odoo mantiene reglas de respaldo por texto:

- Frases como `acepto`, `quiero esa`, `comprar`, `me sirve`, `opción 1` aceptan la recomendada.
- Frases como `me quedo con la batería`, `sin entregar`, `no entrego`, `no dejo` marcan `customer_leaves_old_battery = False`.

Cuando se envia la bateria recomendada, el servicio guarda en la sesion:

- `selected_battery_option_id`
- `selected_battery_price`
- `customer_leaves_old_battery = True` por defecto

Cuando se crea el link Wompi, guarda:

- `wompi_payment_link_id`
- `wompi_payment_url`
- `step = "dispatch_requested"`

Proteccion importante:

Antes de responder a n8n, si `should_send=True` pero `reply` esta vacio, el servicio cambia `should_send=False` y registra warning. Esto evita errores de WhatsApp por mensajes vacios.

## Logs y pruebas utiles

Comandos usados para revisar el problema Wompi:

```bash
rg -n "Wompi|WOMPI|payment link failed|private key|registramos tu interés" /home/programador/developer/odoo18/log/odoo.log
```

Consulta segura de parametros Wompi sin mostrar secretos:

```bash
docker exec mega_work_18-db-1 psql -U odoo -d mega_2026_04_27_1 -tAc "select key, case when value is null or value='' then 'empty' else 'set' end from ir_config_parameter where lower(key) like '%wompi%' order by key;"
```

Resultado visto en esta base:

```text
wompi.private_key|set
wompi.private_key_mega|set
wompi.private_key_mega_test|set
wompi.private_key_test|set
```

Pruebas aisladas hechas:

- Con llave Wompi mockeada:
  - `step = dispatch_requested`
  - `should_send = True`
  - respuesta contiene URL de checkout
  - guarda `wompi_payment_link_id`
  - guarda `wompi_payment_url`

- Sin llave Wompi:
  - `step = advisor_handoff`
  - `should_send = True`
  - respuesta fallback tiene texto

- Confirmacion natural:
  - `todo bien` -> `catalog_sent`
  - `corrige la ubicación` -> `ask_name`
  - `intent=confirm_data_correct` -> `catalog_sent`
  - `intent=correct_data` -> `ask_name`

Verificacion de sintaxis:

```bash
python3 -m compileall -q odoo18/mega_apps/mega_n8n_crm_connector
```

## Seguridad

Los endpoints activos son publicos y no tienen validacion por token:

```python
auth="public"
csrf=False
```

Esto facilita integracion con n8n, pero si las rutas quedan expuestas a internet, conviene agregar autenticacion.

El controlador heredado `n8n_partner_controller.py` si tiene validacion por token, pero no esta activo.

Recomendacion tecnica:

- Agregar token compartido entre n8n y Odoo en los endpoints activos.
- Validar origen o firma si WhatsApp/n8n queda expuesto publicamente.
- Evitar hardcodear secretos.

## Dependencias reales no declaradas explicitamente

El manifiesto solo declara `base` y `crm`, pero el codigo usa modelos que pueden venir de otros modulos:

- `fleet.vehicle.model.brand`
- `fleet.vehicle.model`
- `crm.team`
- `mega.battery.application`
- `mega.battery.application.option`
- Campo `crm_fecha_instalacion` en `crm.lead`
- Campo `brand_id` en `crm.lead`
- Campo `modelo_id` en `crm.lead`
- Campo `year_vehicule_id` en `crm.lead`

Si esos modelos/campos no existen en una base, algunas partes pueden fallar o simplemente no escribir esos datos. Varias escrituras verifican existencia del campo antes de usarlo, pero la busqueda de catalogo si asume modelos `mega.battery.*`.

## Archivos auxiliares o duplicados

`services/whatsapp_ai_service.py` contiene una funcion `_get_n8n_payload()` muy parecida a `helpers/n8n_payload_helper.py`. No parece usada por el flujo activo.

`controllers/n8n_partner_controller.py` contiene logica duplicada y antigua. No esta activo, pero puede confundir en mantenimiento.

`helpers/whatsapp_session_helper.py` contiene funciones de bienvenida antiguas duplicadas frente a `helpers/whatsapp_messages.py`.

## Puntos de atencion para proximos cambios

- Unificar o eliminar `controllers/n8n_partner_controller.py` si ya no se usara.
- Agregar seguridad a los endpoints activos.
- Declarar en `__manifest__.py` las dependencias reales si el addon requiere catalogo, fleet o campos personalizados.
- Mantener monitoreado Wompi: ya esta integrado, pero cualquier llave nueva debe agregarse a los aliases o configurarse en el parametro recomendado.
- El estado `more_catalog_sent` ya reutiliza la misma salida hacia Wompi que `catalog_sent`: si el cliente elige una opcion clara del catalogo adicional, se guarda la opcion seleccionada y se genera link de pago.
- Revisar el paso posterior a `dispatch_requested`: falta definir confirmacion de pago, despacho y cierre final.
- Revisar si `battery_selected` sigue siendo necesario o si debe eliminarse en una limpieza posterior.
- Evitar duplicidad entre `whatsapp_session_helper.py`, `whatsapp_messages.py` y el controlador heredado.
- Considerar tests para reapertura de sesiones, confirmacion, fuera de cobertura, creacion de lead y catalogo.

## Mejora reciente: seleccion desde catalogo adicional

Fecha de implementacion: 2026-05-29.

Se agrego soporte funcional para el estado `more_catalog_sent`, usado cuando el cliente pide mas opciones despues de recibir la bateria recomendada.

Comportamiento esperado:

- Si la sesion esta en `catalog_sent` y el cliente pide mas opciones, el siguiente estado es `more_catalog_sent`.
- Si la sesion esta en `more_options_sent` o `more_catalog_sent`, Odoo envia el catalogo adicional con `build_more_battery_options_message_for_lead()`.
- Si el cliente responde con una opcion clara (`opcion 1`, `opcion 2`, `la 3`, `2`, etc.), la sesion pasa a `payment_link_sent`.
- El servicio interpreta el indice elegido con `_parse_selected_catalog_option()`.
- La opcion elegida se busca con `get_battery_option_for_catalog_index()`, usando el mismo orden de `find_battery_options_for_lead()` que construye el catalogo.
- La seleccion se guarda en la sesion con `_store_catalog_battery_on_session()`:
  - `selected_battery_option_id`
  - `selected_battery_price`
  - `customer_leaves_old_battery`
- La creacion del link de pago se centraliza en `_create_wompi_payment_response()`, compartida por catalogo recomendado y catalogo adicional.
- Si el cliente conserva la bateria usada, se suma `OLD_BATTERY_SURCHARGE` (`40000`) antes de crear el link Wompi.
- Si el cliente solo pregunta el precio sin entregar la bateria usada, se responde el valor con recargo y no se genera link de pago hasta que elija comprar.
- Si el cliente pide asesor, pasa a `advisor_handoff`.
- Si el cliente pide mas opciones nuevamente, no genera link de pago.
- Si el cliente responde algo ambiguo como `acepto` estando en `more_catalog_sent`, no se cobra por defecto; se pide confirmacion de la opcion.

Campos de IA relacionados:

```json
{
  "intent": "select_catalog_option",
  "selected_catalog_option": 2,
  "customer_leaves_old_battery": true
}
```

Intenciones soportadas para `more_options_sent` y `more_catalog_sent`:

- `select_catalog_option`
- `ask_price_without_old_battery`
- `request_more_options`
- `request_advisor`
- `unknown`

Pruebas manuales realizadas con stubs:

- `opcion 2 y dejo la usada` en `more_catalog_sent` devuelve `payment_link_sent`.
- `2` en `more_catalog_sent` devuelve `payment_link_sent`.
- `acepto` en `more_catalog_sent` permanece en `more_catalog_sent` y pide indicar opcion.
- `muestrame mas opciones` en `more_catalog_sent` no genera Wompi.
- `quiero asesor` en `more_catalog_sent` pasa a `advisor_handoff`.
- `_parse_selected_catalog_option()` reconoce `selected_catalog_option`, `quiero la 2` y respuesta numerica exacta.
- `_store_catalog_battery_on_session()` guarda el ID y precio de la opcion seleccionada por indice.

Verificacion tecnica:

```bash
python3 -m compileall -q odoo18/mega_apps/mega_n8n_crm_connector
```

Resultado: sin errores de sintaxis.

## Mapa rapido de responsabilidades

- `controllers/whatsapp_flow_controller.py`: publica las rutas activas para n8n.
- `helpers/services/whatsapp_flow_service.py`: orquesta el flujo principal.
- `helpers/n8n_payload_helper.py`: normaliza payload JSON directo o JSON-RPC.
- `helpers/whatsapp_session_helper.py`: administra sesiones, estados, reapertura, parseo de IA y transiciones.
- `helpers/whatsapp_ai_prompt.py`: genera el prompt grande para IA.
- `helpers/whatsapp_messages.py`: plantillas de mensajes de WhatsApp.
- `helpers/whatsapp_crm_helper.py`: crea/actualiza contactos y leads.
- `helpers/whatsapp_vehicle_helper.py`: resuelve marca, modelo y ano del vehiculo.
- `helpers/whatsapp_catalog_helper.py`: consulta opciones de bateria y construye mensajes de catalogo.
- `helpers/whatsapp_chatter_helper.py`: registra conversacion en chatter.
- `helpers/wompi_payment_helper.py`: crea links de pago en Wompi para la bateria recomendada.
- `models/mega_whatsapp_sessions.py`: modelo de sesion WhatsApp.
- `models/crm_leads.py`: sincroniza cierre de leads con cierre de sesiones.

## Estado mental del sistema

Este addon debe entenderse como un coordinador de conversacion comercial:

- Odoo guarda la verdad de la sesion.
- n8n transporta mensajes y ejecuta automatizaciones externas.
- La IA interpreta lenguaje natural y devuelve JSON.
- Odoo valida el JSON, aplica reglas, crea CRM y decide el proximo mensaje.
- El asesor humano entra cuando la conversacion ya tiene datos utiles o cuando el flujo no puede resolver automaticamente.

El siguiente trabajo sobre este proyecto deberia partir de esa separacion: n8n no deberia decidir reglas comerciales profundas, la IA no deberia inventar datos ni precios, y Odoo deberia seguir siendo la fuente de estado, CRM y catalogo.
