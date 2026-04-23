# mega_contact_lock_identification

## Descripción

Módulo de personalización para Odoo 18 que controla el flujo de creación y edición de contactos en `res.partner`, con el objetivo de reducir errores de digitación y mejorar la calidad de la información registrada.

Este desarrollo restringe visualmente el formulario de contactos para que el usuario complete primero la identificación del tercero y, a partir de allí, habilite progresivamente el resto de campos.

---

## Objetivo funcional

Evitar que los usuarios diligencien contactos incompletos o con errores de estructura, especialmente en:

- número de identificación
- país
- estado
- ciudad
- dirección
- datos de contacto

El módulo fuerza un orden lógico de captura de información y limita ciertos campos hasta que se cumplan condiciones previas.

---

## Funcionalidades implementadas

### 1. Alertas visuales en el formulario de contactos

Se agregaron alertas informativas en la parte superior del formulario de `res.partner` para guiar al usuario durante la creación del contacto.

#### Flujo de alertas:
1. Ingresar NIT o cédula
2. Seleccionar país
3. Seleccionar estado
4. Ingresar ciudad

Estas alertas aparecen dinámicamente según el avance del diligenciamiento.

---

### 2. Bloqueo progresivo de campos

Se configuró lógica visual para controlar el acceso a diferentes campos del contacto según el valor de la identificación (`vat`).

#### Comportamiento implementado:
- Mientras no exista identificación, se restringe el acceso al resto del formulario.
- La dirección solo se muestra después de ingresar identificación.
- El campo de estado depende del país.
- La ciudad depende del estado.
- Los demás campos del contacto quedan condicionados por la identificación.

---

### 3. Ocultamiento del bloque de dirección hasta ingresar identificación

Se configuró el ocultamiento del bloque visual de dirección (`o_address_format`) y su etiqueta asociada mientras el contacto no tenga número de identificación.

#### Elementos ocultados:
- etiqueta de dirección
- calle
- calle 2
- ciudad
- estado
- código postal
- país

Esto evita que el usuario empiece a diligenciar direcciones antes de registrar el NIT o la cédula.

---

### 4. Bloqueo del nombre del contacto

Los campos de nombre visibles en la cabecera del formulario fueron ajustados para quedar en modo solo lectura mientras no exista identificación.

#### Campos afectados:
- `field id="company"`
- `field id="individual"`

Esto aplica tanto para empresa como para persona.

---

### 5. Control del bloque de relación con empresa

Se revisó y ajustó el comportamiento de los campos relacionados con empresa matriz o empresa asociada en la zona superior del formulario:

- `parent_id`
- `company_name`
- botón `create_company`

Se definió visibilidad controlada según el tipo de contacto y el grupo de seguridad asignado.

---

### 6. Grupo de seguridad para visualización del campo empresa

Se creó un grupo de seguridad para controlar la visibilidad de elementos relacionados con empresa dentro del formulario de contactos.

#### Grupo creado:
- **Company, Module Contact**

#### XML ID:
```xml
group_contact_company_menu_lock
