# Contexto Técnico - Mega Colombia Jersey Landing

Este documento resume el contexto funcional y técnico del módulo `mega_colombia_jersey_landing`.

## Propósito

El módulo fue creado para gestionar por código una landing pública de concurso comercial de Mega Baterías. El concurso busca capturar participantes para ganar una camiseta original de la Selección Colombia y luego permitir seleccionar un ganador desde el backend de Odoo.

La solución evita Odoo Studio y el editor visual del website. Todo queda versionable en código.

## Alcance

El módulo cubre:

- Página pública de registro.
- Validación de formulario.
- Persistencia de participantes.
- Menú backend.
- Consulta de participantes.
- Creación de sorteos.
- Selección aleatoria de ganador.
- Auditoría del sorteo.

No cubre:

- Envío automático de correos.
- Integración con WhatsApp.
- Publicación automática del ganador.
- Validación contra documentos externos.
- Restricciones de duplicados por cédula, celular o correo.

## Website

La landing está limitada al sitio:

```python
CONTEST_WEBSITE_ID = 1
```

Archivo:

```text
controllers/main.py
```

Si `request.website.id` es diferente, el controller responde con 404 usando `NotFound`.

## Rutas

Landing:

```text
GET /mega-fiesta-futbol
```

Formulario:

```text
POST /mega-fiesta-futbol/submit
```

El POST valida campos obligatorios, email básico y autorizaciones antes de crear el registro.

## Modelo de Participantes

Modelo:

```text
mega.jersey.contest.participant
```

Archivo:

```text
models/mega_jersey_contest_participant.py
```

El modelo almacena los datos del formulario:

- Nombre completo
- Cédula
- Celular
- Correo
- Dirección
- Placa
- Marca y modelo
- Servicio adquirido
- Autorizaciones
- Website
- IP
- User Agent
- Estado

Las autorizaciones se validan con constraint:

- Si `accept_data_policy` es falso, lanza `ValidationError`.
- Si `accept_commercial_info` es falso, lanza `ValidationError`.

## Servicio Adquirido

Campo:

```python
service_acquired
```

Tipo:

```text
fields.Selection
```

Opciones:

- `baterias`: Baterías
- `llantas`: Llantas
- `mega_combo`: MegaCombo
- `mecanica_especializada`: Mecánica especializada
- `cambio_aceite`: Cambio de aceite

Este campo es obligatorio y se muestra en:

- Landing pública.
- Lista de participantes.
- Formulario de participante.
- Vista de búsqueda.
- Datos del ganador del sorteo.

## Modelo de Sorteo

Modelo:

```text
mega.jersey.contest.draw
```

Archivo:

```text
models/mega_jersey_contest_draw.py
```

Hereda:

```python
_inherit = ["mail.thread"]
```

Esto permite dejar trazabilidad en chatter.

Campos de auditoría:

- `winner_selection_datetime`
- `winner_selection_user_id`
- `eligible_participant_count`
- `winner_id`
- `state`

## Selección de Ganador

Método:

```python
action_select_winner()
```

Reglas:

- Solo se ejecuta si `state = draft`.
- Busca participantes con ambas autorizaciones en `True`.
- Si no existen participantes válidos, lanza `UserError`.
- Selecciona ganador con `random.choice`.
- Guarda fecha, usuario, cantidad elegible y ganador.
- Cambia estado a `done`.
- Publica mensaje en chatter.
- Devuelve efecto `rainbow_man`.

Una vez realizado:

- No se puede recalcular.
- No se puede modificar el resultado.
- No se puede volver a borrador.
- No se puede eliminar.

## Menú Backend

Menú raíz:

```text
Concurso Camiseta Selección
```

Submenús:

```text
Participantes
Sorteo
```

Archivo:

```text
views/mega_jersey_contest_views.xml
```

## Landing QWeb

Archivo:

```text
views/mega_jersey_contest_templates.xml
```

Templates:

- `template_mega_jersey_landing`
- `template_mega_jersey_thank_you`

La landing es intencionalmente simple:

- Hero compacto.
- Fecha del sorteo visible: 13 de junio.
- Formulario.
- Checkboxes.
- Botón de participación.
- Página de gracias.

No se hereda `website.layout` para mantener la página limpia, sin navbar ni footer.

## Seguridad

Archivo:

```text
security/ir.model.access.csv
```

Acceso:

- `base.group_user`: acceso completo a participantes y sorteos.
- Público: sin acceso directo a modelos.

El controller público usa `sudo()` al crear participantes.

## Dependencias

El módulo depende de:

```python
"mail"
"website"
```

`mail` es necesario para chatter del sorteo.
`website` es necesario para la landing pública.

## Consideraciones de Mantenimiento

- Si cambia el sitio web autorizado, actualizar `CONTEST_WEBSITE_ID` en `controllers/main.py`.
- Si cambian los servicios, actualizar:
  - `service_acquired` en el modelo participante.
  - `SERVICE_OPTIONS` en el controller.
  - `<select>` en el template QWeb.
- Si cambia la fecha del sorteo, actualizar el texto visible en el template.
- Si se requieren reglas de duplicidad, agregarlas con constraint SQL o validación controller/modelo.

## Comandos de Validación Usados

Python:

```bash
python3 -m py_compile ...
```

XML:

```bash
python3 -c "import xml.etree.ElementTree as ET; ET.parse('views/mega_jersey_contest_templates.xml'); ET.parse('views/mega_jersey_contest_views.xml')"
```
