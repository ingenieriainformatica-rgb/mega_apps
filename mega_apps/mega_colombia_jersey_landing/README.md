# Mega Colombia Jersey Landing

Módulo Odoo 18 para publicar una landing pública del concurso:

**“Gánate la camiseta original de la Selección Colombia para que vivas la MEGA fiesta del fútbol”**

El módulo permite capturar participantes desde una página web pública y administrar el concurso desde el backend de Odoo, incluyendo participantes, sorteo aleatorio, ganador y trazabilidad.

## Funcionalidades

- Landing pública en `/mega-fiesta-futbol`.
- Formulario de participación responsive y con estilo Mega.
- Captura de datos personales, vehículo y servicio adquirido.
- Checkboxes obligatorios de autorización.
- Página de confirmación después del envío.
- Backend para consultar participantes.
- Backend para crear sorteos y seleccionar ganador aleatorio.
- Auditoría del sorteo con chatter.
- Restricción de la landing al `website_id = 1`.

## Landing Pública

Ruta:

```text
/mega-fiesta-futbol
```

Ruta de envío:

```text
/mega-fiesta-futbol/submit
```

La landing solo funciona cuando el sitio actual tiene:

```python
website_id = 1
```

Si el sitio actual no corresponde, el controller devuelve 404.

## Datos Capturados

Modelo:

```text
mega.jersey.contest.participant
```

Campos principales:

- Nombre completo
- Cédula
- Número de celular
- Correo electrónico
- Dirección
- Placa
- Marca y modelo
- Servicio adquirido
- Autorización tratamiento de datos
- Autorización información comercial
- Sitio web
- IP
- User Agent
- Estado

Servicios disponibles:

- Baterías
- Llantas
- MegaCombo
- Mecánica especializada
- Cambio de aceite

## Backend

Menú principal:

```text
Concurso Camiseta Selección
```

Opciones:

- Participantes
- Sorteo

## Sorteo

Modelo:

```text
mega.jersey.contest.draw
```

El sorteo permite seleccionar un ganador aleatorio entre participantes válidos.

Participantes válidos:

- `accept_data_policy = True`
- `accept_commercial_info = True`

El botón **Seleccionar ganador**:

- Solo aparece cuando el sorteo está en borrador.
- Usa `random.choice` para seleccionar el ganador.
- Guarda el ganador.
- Guarda fecha y hora de selección.
- Guarda el usuario que ejecutó el sorteo.
- Guarda la cantidad de participantes elegibles.
- Cambia el estado a realizado.
- Publica un mensaje de auditoría en el chatter.
- Muestra efecto `rainbow_man`.

Después de realizado, el sorteo queda congelado:

- No se puede recalcular.
- No se puede modificar el ganador.
- No se puede devolver a borrador.
- No se puede eliminar.

## Seguridad

Archivo:

```text
security/ir.model.access.csv
```

Permisos:

- Usuarios internos (`base.group_user`) pueden leer, crear, escribir y eliminar participantes y sorteos.
- El público no tiene acceso directo al modelo.
- El formulario público crea participantes mediante controller usando `sudo()`.

## Instalación / Actualización

1. Asegurar que el módulo esté en el addons path.
2. Actualizar lista de aplicaciones si es la primera instalación.
3. Instalar o actualizar:

```text
mega_colombia_jersey_landing
```

Después de cambios en XML o Python, actualizar el módulo en Odoo.

## Dependencias

```python
depends = [
    "mail",
    "website",
]
```

## Archivos Principales

```text
__manifest__.py
controllers/main.py
models/mega_jersey_contest_participant.py
models/mega_jersey_contest_draw.py
views/mega_jersey_contest_templates.xml
views/mega_jersey_contest_views.xml
security/ir.model.access.csv
```

## Notas

- La fecha visible del sorteo en la landing es el **13 de junio**.
- El diseño de la landing está definido por código en QWeb, no por Odoo Studio.
- No se usa editor visual de website.
- La lógica se mantiene simple para estabilidad y facilidad de mantenimiento.
