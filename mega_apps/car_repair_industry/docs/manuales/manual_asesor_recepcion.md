---
title: "Manual de Usuario — Taller de Autos"
subtitle: "Rol: Asesor de Recepción"
author: "MegaTecnicentro"
date: "Junio 2026"
version: "1.0"
lang: es
---

\newpage

# MANUAL DE USUARIO
# Sistema de Taller de Autos — Odoo 18

---

**Rol:** Asesor de Recepción  
**Versión:** 1.0  
**Fecha:** Junio 2026  
**Sistema:** MegaTecnicentro — Portal de Taller

---

\newpage

## Tabla de contenido

1. [Introducción](#introducción)
2. [Requisitos previos](#requisitos-previos)
3. [Acceso al sistema](#acceso-al-sistema)
4. [Crear una nueva orden de trabajo](#crear-una-nueva-orden-de-trabajo)
   - Paso 1 — Tipo de cliente
   - Paso 2 — Datos del cliente
   - Paso 3 — Datos del vehículo
   - Paso 4 — Servicio solicitado
   - Paso 5 — Persona que entrega el vehículo
   - Paso 6 — Pertenencias y documentos
   - Paso 7 — Evidencias fotográficas
   - Paso 8 — Checklist de recepción
5. [Guardar la orden](#guardar-la-orden)
6. [Buenas prácticas](#buenas-prácticas)
7. [Preguntas frecuentes](#preguntas-frecuentes)
8. [Glosario de términos](#glosario-de-términos)

\newpage

---

## 1. Introducción

### 1.1 Objetivo del rol

El **Asesor de Recepción** es la persona encargada de recibir los vehículos en el taller y registrar toda la información necesaria para iniciar el proceso de reparación o mantenimiento. Su trabajo es el primer paso del flujo operativo y su correcta ejecución garantiza que el técnico cuente con todos los datos para realizar su trabajo.

### 1.2 Responsabilidades del Asesor de Recepción

- Identificar correctamente al cliente y el tipo de servicio que solicita.
- Registrar los datos completos del vehículo en el sistema.
- Documentar el estado del vehículo al momento de ingreso.
- Registrar los servicios solicitados por el cliente.
- Anotar las pertenencias y documentos recibidos junto al vehículo.
- Tomar fotografías de evidencia cuando corresponda.
- Diligenciar el checklist de recepción según la plantilla asignada.

> **Nota importante:** El Asesor de Recepción únicamente tiene acceso al portal web para crear órdenes de trabajo. No tiene acceso al sistema administrativo interno (backend) de Odoo.

\newpage

---

## 2. Requisitos previos

Antes de utilizar el sistema, asegúrese de contar con lo siguiente:

| Requisito | Descripción |
|---|---|
| **Usuario** | Nombre de usuario o correo electrónico asignado por el administrador |
| **Contraseña** | Contraseña provisional entregada en el proceso de activación |
| **Dispositivo** | Computador, tableta o celular con conexión a internet |
| **Navegador** | Google Chrome, Microsoft Edge, Mozilla Firefox o Safari (versiones recientes) |
| **Conexión** | Acceso a internet estable |

> Si no tiene usuario o contraseña, comuníquese con el administrador del sistema antes de continuar.

\newpage

---

## 3. Acceso al sistema

### 3.1 Ingreso al portal

1. Abra el navegador de internet en su dispositivo.
2. Escriba en la barra de direcciones la URL del sistema proporcionada por el administrador.
3. Presione **Enter** para cargar la página.

[CAPTURA 1 — Pantalla de inicio de sesión del portal]

> *El usuario verá una pantalla con el logotipo de la empresa y dos campos: uno para el correo electrónico y otro para la contraseña. En la parte inferior hay un botón azul que dice "Iniciar sesión".*

### 3.2 Inicio de sesión

1. En el campo **Correo electrónico**, escriba su correo o nombre de usuario asignado.
2. En el campo **Contraseña**, escriba su contraseña.
3. Haga clic en el botón **Iniciar sesión**.

Si los datos son correctos, el sistema lo llevará automáticamente al panel del taller (`/my/workshop`).

[CAPTURA 2 — Panel principal del taller (pantalla /my/workshop)]

> *El usuario verá el panel de órdenes de trabajo con tarjetas que muestran el resumen de cada orden. En la parte superior derecha hay un botón verde que dice "Nueva orden de servicio".*

### 3.3 Problemas de acceso

| Problema | Solución |
|---|---|
| "Nombre de usuario o contraseña incorrectos" | Verifique mayúsculas y espacios. Si persiste, contacte al administrador para restablecer la contraseña. |
| La página no carga | Verifique la conexión a internet. Intente con otro navegador. |
| No aparece el botón "Nueva orden de servicio" | Su usuario no tiene permisos de Asesor de Recepción. Contacte al administrador. |

\newpage

---

## 4. Crear una nueva orden de trabajo

Para crear una nueva orden, haga clic en el botón **Nueva orden de servicio** ubicado en la parte superior del panel.

El sistema lo llevará al formulario de creación en la dirección `/my/workshop/order/new`.

[CAPTURA 3 — Vista completa del formulario de nueva orden de trabajo]

> *El formulario está organizado en 8 secciones numeradas. Cada sección tiene un título y un número circular de color verde a la izquierda. Los campos marcados con un asterisco rojo (\*) son obligatorios.*

El formulario se compone de las siguientes secciones:

| N° | Sección | Descripción |
|---|---|---|
| 1 | Tipo de cliente | Identifica si es cliente particular, Renting o corporativo |
| 2 | Datos del cliente | Información de contacto del propietario del vehículo |
| 3 | Datos del vehículo | Placa, marca, modelo y características técnicas |
| 4 | Servicio solicitado | Tipo de trabajo que se va a realizar |
| 5 | Persona que entrega | Datos de quien trae el vehículo físicamente |
| 6 | Pertenencias y documentos | Objetos de valor y documentos recibidos con el vehículo |
| 7 | Evidencias fotográficas | Fotos del vehículo al momento del ingreso |
| 8 | Checklist de recepción | Lista de verificación del estado del vehículo |

> Llene el formulario de arriba hacia abajo en orden. No omita las secciones obligatorias.

---

### Paso 1 — Tipo de cliente

[CAPTURA 4 — Sección 1: Tipo de cliente con las tres opciones visibles]

> *El usuario verá tres tarjetas grandes: "Renting" (ícono de edificio), "Particular" (ícono de persona, seleccionada por defecto) y "Corporativo" (ícono de maletín). Hacer clic en una tarjeta la selecciona y cambia la sección 2 del formulario.*

El formulario muestra tres opciones:

| Opción | Descripción | Cuándo usarla |
|---|---|---|
| **Renting** | Flotas de empresas de alquiler | Cuando el vehículo pertenece a la empresa de Renting registrada en el sistema |
| **Particular** | Persona natural | Cuando el cliente es una persona que lleva su propio vehículo *(opción predeterminada)* |
| **Corporativo** | Empresa con flota propia | Cuando el vehículo pertenece a una empresa cliente distinta a Renting |

**Cómo seleccionar:** Haga clic sobre la tarjeta correspondiente. La tarjeta seleccionada quedará resaltada con un borde de color verde.

> **Importante:** La selección del tipo de cliente cambia automáticamente los campos que se muestran en la sección 2. Seleccione el tipo correcto antes de continuar.

---

### Paso 2 — Datos del cliente

Los campos de esta sección varían según el tipo de cliente seleccionado en el Paso 1.

---

#### Opción A: Cliente Particular

[CAPTURA 5 — Sección 2 con tipo "Particular" seleccionado]

| Campo | Obligatorio | Descripción | Ejemplo |
|---|---|---|---|
| **Nombre del cliente** | **Sí \*** | Nombre completo del propietario del vehículo | `Carlos Andrés Pérez Gómez` |
| **Celular** | No | Número de teléfono celular del cliente | `300 123 4567` |
| **Correo** | No | Dirección de correo electrónico | `carlos@correo.com` |

---

#### Opción B: Cliente Renting

[CAPTURA 6 — Sección 2 con tipo "Renting" seleccionado]

Al seleccionar Renting, el sistema muestra automáticamente los datos de la empresa Renting registrada (nombre, NIT, teléfono, correo). El asesor solo debe completar:

| Campo | Obligatorio | Descripción | Ejemplo |
|---|---|---|---|
| **CI / referencia Renting** | No | Número de referencia o código interno de la cita de Renting | `CI-12345` |
| **Cita Renting validada** | No | Marque esta casilla si la cita fue previamente validada con Renting | *(casilla de verificación)* |

> **Nota:** Para clientes Renting, los campos **Nombre** y **Celular** de la sección 5 (Persona que entrega el vehículo) se vuelven **obligatorios**.

---

#### Opción C: Cliente Corporativo

[CAPTURA 7 — Sección 2 con tipo "Corporativo" seleccionado]

| Campo | Obligatorio | Descripción | Ejemplo |
|---|---|---|---|
| **Razón social** | **Sí \*** | Nombre legal completo de la empresa | `Transportes XYZ S.A.S.` |
| **NIT** | No | Número de identificación tributaria de la empresa | `900123456-7` |
| **Correo corporativo** | No | Correo electrónico de la empresa | `contacto@empresa.com` |

> **Consejo:** Si el NIT ya está registrado en el sistema, el sistema reconocerá automáticamente a la empresa y no la duplicará. Ingrese siempre el NIT cuando lo conozca.

> **Nota:** Para clientes Corporativos, los campos **Nombre** y **Celular** de la sección 5 se vuelven **obligatorios**.

---

### Paso 3 — Datos del vehículo

[CAPTURA 8 — Sección 3: Datos del vehículo con todos los campos visibles]

Esta sección permite registrar la identificación y las características técnicas del vehículo.

#### Campos obligatorios

| Campo | Obligatorio | Descripción | Ejemplo |
|---|---|---|---|
| **Placa** | **Sí \*** | Número de placa del vehículo. Se convierte automáticamente a mayúsculas | `ABC123` |

#### Campos opcionales

| Campo | Descripción | Ejemplo |
|---|---|---|
| **Marca** | Fabricante del vehículo. Seleccione de la lista desplegable | `Renault` |
| **Línea** | Referencia o línea del vehículo. Solo se activa después de seleccionar la Marca | `Logan` |
| **Modelo (año)** | Año de fabricación del vehículo. Ingrese solo el año (4 dígitos) | `2019` |
| **Cilindraje (cc)** | Capacidad del motor en centímetros cúbicos | `1598` |
| **Nº de motor** | Número de serie del motor. Se convierte a mayúsculas automáticamente | `K7MA7123456` |
| **Nº de chasis (VIN)** | Número de identificación vehicular. Máximo 32 caracteres | `9FB3XXBBD0BH00001` |
| **Tipo de combustible** | Seleccione el tipo de combustible del vehículo | `Gasolina` |
| **Kilometraje** | Lectura del odómetro al momento del ingreso | `85000` |
| **Nivel de combustible** | Indicador del nivel de combustible al recibir el vehículo | `1/2` |

#### Opciones disponibles para Tipo de combustible

Gasolina · Diésel · Híbrido · Híbrido enchufable (gasolina) · Híbrido enchufable (diésel) · GNC · GLP · Hidrógeno · Eléctrico · Híbrido (otro)

#### Opciones disponibles para Nivel de combustible

Vacío · Reserva · 1/4 · 1/2 · 3/4 · Lleno

> **Buena práctica:** Registre siempre el kilometraje y el nivel de combustible. Estos datos protegen tanto al cliente como al taller ante posibles reclamaciones.

> **Importante sobre la Línea:** El campo "Línea" solo muestra opciones después de haber seleccionado una "Marca".

---

### Paso 4 — Servicio solicitado

[CAPTURA 9 — Sección 4: Servicios solicitados con casillas de verificación y campos de motivo]

Esta sección define qué trabajo debe realizarse al vehículo.

#### Servicios solicitados (obligatorio — al menos uno)

Los servicios disponibles aparecen como tarjetas con casillas de verificación. Puede seleccionar **más de un servicio** en la misma orden.

> **Importante:** Debe seleccionar al menos un servicio. Si no selecciona ninguno, el sistema mostrará un error y no le permitirá guardar la orden.

#### Plantilla checklist

| Campo | Descripción |
|---|---|
| **Plantilla checklist** | Seleccione la plantilla de inspección que corresponde al tipo de servicio. La plantilla predeterminada aparece preseleccionada. |

> La selección de la plantilla determina qué ítems aparecerán en la sección 8 (Checklist de recepción).

#### Motivo de ingreso (obligatorio)

| Campo | Obligatorio | Descripción | Ejemplo |
|---|---|---|---|
| **Motivo de ingreso** | **Sí \*** | Descripción breve del motivo por el cual el cliente trae el vehículo | `Mantenimiento preventivo 10.000 km` |

> Sea específico en el motivo. Una descripción clara ayuda al técnico a entender el problema antes de ver el vehículo.

---

### Paso 5 — Persona que entrega el vehículo

[CAPTURA 10 — Sección 5: Datos de quien entrega el vehículo]

Esta sección registra los datos de la persona que **físicamente entrega el vehículo** en el taller. Esta persona puede ser diferente al propietario.

| Campo | Obligatorio | Descripción | Ejemplo |
|---|---|---|---|
| **Nombre** | **Sí\*** *(Renting y Corporativo)* / No *(Particular)* | Nombre completo de quien entrega el vehículo | `Juan David Ramírez` |
| **Celular** | **Sí\*** *(Renting y Corporativo)* / No *(Particular)* | Número de contacto de quien entrega | `315 987 6543` |
| **Documento** | No | Número de cédula o documento de identificación | `1020304050` |
| **Correo** | No | Dirección de correo electrónico de quien entrega | `jramrez@empresa.com` |
| **Observaciones de quien entrega** | No | Cualquier indicación o novedad comunicada por quien trae el vehículo | `El cliente indica que el ruido aparece solo en frío` |

> **Cuándo es obligatorio Nombre y Celular:** Si seleccionó tipo de cliente **Renting** o **Corporativo**, estos dos campos son obligatorios. Para clientes **Particulares** son opcionales.

---

### Paso 6 — Pertenencias y documentos

[CAPTURA 11 — Sección 6: Pertenencias y documentos]

Esta sección permite registrar los objetos y documentos que el cliente deja dentro del vehículo o entrega al taller.

| Campo | Obligatorio | Descripción | Ejemplo |
|---|---|---|---|
| **¿Tiene objetos de valor?** | No | Indique si el cliente dejó objetos de valor dentro del vehículo | `Sí` |
| **Pertenencias / objetos de valor** | No | Describa qué objetos de valor se encontraron o reportó el cliente | `Celular iPhone en la guantera, gafas de sol en el tablero` |
| **Documentos recibidos** | No | Liste los documentos que el cliente entregó con el vehículo | `Tarjeta de propiedad, SOAT vigente` |
| **Observaciones generales de recepción** | No | Anote cualquier novedad importante al recibir el vehículo | `Vehículo llega con rayón en guardabarro trasero izquierdo (preexistente)` |

> **Importante:** Si el cliente reporta objetos de valor dentro del vehículo, regístrelos siempre. Esto protege al taller ante posibles reclamaciones posteriores.

---

### Paso 7 — Evidencias fotográficas

[CAPTURA 12 — Sección 7: Área de carga de fotografías con la zona de arrastre visible]

Esta sección permite registrar fotografías del estado del vehículo al momento del ingreso.

#### Cómo cargar fotografías

1. Haga clic en el rectángulo punteado que dice **"Seleccionar fotos"**.
2. Se abrirá el explorador de archivos de su dispositivo.
3. Seleccione una o varias fotografías (puede seleccionar varias a la vez manteniendo presionada la tecla `Ctrl`).
4. Haga clic en **Abrir** o **Aceptar**.
5. Las fotos aparecerán como miniaturas en la pantalla.
6. Para cada foto, seleccione la **categoría** correspondiente en el menú desplegable.

#### Formatos aceptados

JPG / JPEG · PNG · WEBP

#### Categorías disponibles para las fotografías

| Categoría | Cuándo usarla |
|---|---|
| **Externa** | Fotos del exterior del vehículo (carrocería, puertas, capó, maletero) |
| **Interna** | Fotos del interior (tablero, asientos, piso) |
| **Daño existente** | Fotos de golpes, rayones o daños preexistentes |
| **Pertenencias** | Fotos de los objetos de valor dentro del vehículo |
| **Documentos** | Fotos de documentos entregados con el vehículo |
| **Otro** | Cualquier otra evidencia que no encaje en las categorías anteriores |

#### Descripción del lote

| Campo | Descripción | Ejemplo |
|---|---|---|
| **Descripción del lote** | Nota general que aplica a todas las fotos de esta carga | `Evidencia de ingreso. Rayón preexistente en guardabarro derecho.` |

> Para eliminar una foto antes de guardar, haga clic en el ícono de papelera que aparece en la esquina de cada miniatura.

---

### Paso 8 — Checklist de recepción

[CAPTURA 13 — Sección 8: Checklist con tabla de ítems, columna de estado y observaciones]

Esta sección aparece únicamente cuando se seleccionó una **Plantilla checklist** en la sección 4.

#### Opciones de estado por ítem

| Estado | Significado |
|---|---|
| **Bueno** | El componente está en buen estado |
| **Regular** | El componente presenta desgaste pero funciona |
| **Malo** | El componente está dañado o no funciona |
| **No aplica** | El ítem no corresponde a este tipo de vehículo o servicio |

#### Cómo diligenciar el checklist

1. Para cada ítem de la lista, seleccione el estado en el menú desplegable de la columna **Estado**.
2. Si el ítem presenta alguna observación relevante, escríbala en la columna **Observación**.
3. Complete todos los ítems que apliquen.

\newpage

---

## 5. Guardar la orden

Una vez que haya completado todos los campos necesarios, proceda a guardar la orden.

### Cómo guardar

1. Baje hasta el final del formulario.
2. Haga clic en el botón que dice **"Crear orden de servicio"**.

[CAPTURA 14 — Barra de acciones al final del formulario con el botón "Crear orden de servicio"]

### ¿Qué sucede después de guardar?

1. El sistema verifica que todos los campos obligatorios estén completos.
2. Si todo está correcto, la orden se crea automáticamente y el sistema le asigna un **número de referencia** (por ejemplo: `OT-00045`).
3. El sistema lo redirige automáticamente a la página de detalle de la orden.
4. La orden aparecerá en el panel principal con el estado **"Por asignar"**.

[CAPTURA 15 — Página de confirmación / detalle de la orden recién creada]

### Cómo identificar que la orden fue creada correctamente

- ✅ El sistema lo lleva a una nueva página (el detalle de la orden).
- ✅ En la parte superior aparece el **número de referencia** de la orden.
- ✅ El estado de la orden muestra **"Por asignar"**.
- ✅ Al regresar al panel, la nueva orden aparece en la lista de tarjetas.

### Errores al guardar

| Mensaje de error | Causa | Solución |
|---|---|---|
| Campo marcado en rojo sin diligenciar | Un campo obligatorio está vacío | Complete todos los campos con asterisco rojo (\*) |
| "Debe seleccionar al menos un servicio" | No se marcó ningún servicio en la sección 4 | Seleccione al menos un tipo de servicio |
| "Debe registrar el nombre del cliente particular" | El campo Nombre del cliente está vacío para tipo Particular | Complete el nombre del cliente |
| "Para Renting debe registrar nombre y celular de quien entrega el vehículo" | Tipo Renting seleccionado pero la sección 5 está incompleta | Complete Nombre y Celular en la sección 5 |
| "Para Corporativo debe registrar la razón social de la empresa" | Tipo Corporativo seleccionado pero falta la razón social | Complete la Razón social en la sección 2 |
| "Para Corporativo debe registrar nombre y celular de quien entrega el vehículo" | Tipo Corporativo seleccionado pero la sección 5 está incompleta | Complete Nombre y Celular en la sección 5 |

\newpage

---

## 6. Buenas prácticas

### 6.1 Verificación de la placa

- Confirme la placa directamente con el vehículo físico, no con el cliente de memoria.
- Revise que la placa registrada en el sistema coincida exactamente con la del vehículo.
- La placa se guarda en **mayúsculas** automáticamente; no es necesario que la escriba en mayúsculas.
- Si hay alguna duda sobre la placa, consulte la tarjeta de propiedad del vehículo.

### 6.2 Verificación de datos del cliente

- Para clientes **Particulares**: confirme el nombre completo (no abreviaturas).
- Para clientes **Corporativos**: solicite siempre el NIT para evitar duplicar el contacto en el sistema.
- Para clientes **Renting**: verifique que la cita haya sido previamente aprobada y registre el número de referencia.

### 6.3 Descripción de servicios y motivo de ingreso

Sea específico en el campo **Motivo de ingreso**. Evite descripciones genéricas:

- ❌ **Incorrecto:** `Problema con el carro`
- ✅ **Correcto:** `Ruido fuerte en la suspensión delantera derecha al pasar por baches`

Seleccione **todos** los servicios que el cliente solicita, no solo el principal.

### 6.4 Registro del estado del vehículo

- Registre siempre el **kilometraje** leyendo directamente el tablero del vehículo.
- Registre el **nivel de combustible** observando el indicador del tablero.
- Anote en **Observaciones generales de recepción** cualquier daño visible en la carrocería antes del ingreso.

### 6.5 Evidencias fotográficas

- Tome fotografías de los **4 lados del vehículo** (frente, trasera, lado izquierdo, lado derecho).
- Tome fotos detalladas de **daños preexistentes** y clasifíquelos en la categoría "Daño existente".
- Si el cliente reporta objetos de valor, **fotografíe los objetos** y clasifíquelos en "Pertenencias".

### 6.6 No presionar "Cancelar" por error

El botón **Cancelar** descarta todos los datos ingresados en el formulario. Si cerró el formulario por error antes de guardar, deberá iniciar el registro desde cero.

\newpage

---

## 7. Preguntas frecuentes

**¿Puedo crear una orden sin seleccionar la marca y el modelo del vehículo?**

Sí. La Marca, Línea y Modelo (año) son campos opcionales. Sin embargo, se recomienda completarlos para facilitar el trabajo del técnico.

---

**¿Qué pasa si el cliente ya está registrado en el sistema?**

El sistema identifica a los clientes por celular o correo (para Particulares) y por NIT (para Corporativos). Si el cliente ya existe, el sistema lo vincula automáticamente sin crear un duplicado.

---

**¿Puedo registrar más de un servicio en una sola orden?**

Sí. El formulario permite seleccionar múltiples servicios para la misma orden haciendo clic en cada tarjeta de servicio.

---

**¿Qué debo hacer si no encuentro la marca del vehículo en la lista?**

Si la marca no aparece en la lista desplegable, deje el campo en blanco y anote la marca en el campo **Motivo de ingreso** o en **Observaciones generales de recepción**. Notifique al administrador para que la agregue al sistema.

---

**¿Puedo editar una orden después de crearla?**

El Asesor de Recepción **no tiene permisos para editar órdenes** una vez guardadas. Si necesita corregir un dato, comuníquese con el administrador del sistema.

---

**¿Qué hace el sistema con las fotografías que cargo?**

Las fotografías se almacenan en Google Drive vinculado al taller. Quedan disponibles en el detalle de la orden. No se guardan en el dispositivo del asesor.

---

**¿Qué significa el estado "Por asignar"?**

"Por asignar" es el estado inicial de toda orden recién creada. Indica que la orden fue registrada correctamente y está esperando que el jefe de taller le asigne un técnico.

---

**¿El checklist de la sección 8 es obligatorio?**

No. El checklist aparece solo si hay una plantilla seleccionada. Diligenciarlo correctamente mejora la calidad del servicio, pero el sistema permite guardar la orden aunque no se complete.

---

**¿Qué hago si la página muestra un error diferente a los descritos en el manual?**

Tome una captura de pantalla del error, anote la hora en que ocurrió y comuníquese con el administrador del sistema.

---

**¿Puedo usar el sistema desde mi celular?**

Sí. El portal está diseñado para funcionar en celular, tableta y computador. En celulares, los campos se reorganizan verticalmente.

\newpage

---

## 8. Glosario de términos

| Término | Definición |
|---|---|
| **Asesor de Recepción** | Persona encargada de recibir los vehículos en el taller y registrar la información inicial en el sistema |
| **Orden de trabajo** | Registro digital que documenta el ingreso de un vehículo al taller y los servicios a realizar |
| **Portal** | Interfaz web de Odoo accesible desde el navegador, diferente al sistema administrativo interno |
| **Placa** | Número de identificación vehicular asignado por el organismo de tránsito |
| **VIN / Nº de chasis** | Número de Identificación Vehicular. Código único de 17 caracteres grabado en el chasis |
| **Nº de motor** | Número de serie grabado directamente en el bloque del motor del vehículo |
| **Cilindraje (cc)** | Capacidad volumétrica del motor medida en centímetros cúbicos |
| **Kilometraje** | Lectura del odómetro del vehículo que indica la distancia total recorrida en kilómetros |
| **Renting** | Modalidad de flota vehicular en la que los vehículos pertenecen a una empresa de alquiler a largo plazo |
| **Cliente Corporativo** | Empresa que tiene flota propia de vehículos y los lleva al taller para mantenimiento |
| **CI / Referencia Renting** | Código de identificación de la cita o contrato asignado por la empresa Renting |
| **Cita Renting validada** | Confirmación de que la empresa Renting aprobó previamente el ingreso del vehículo al taller |
| **Checklist de recepción** | Lista de verificación estandarizada que documenta el estado de los componentes del vehículo al ingreso |
| **Plantilla checklist** | Formato predefinido con los ítems específicos que se deben revisar según el tipo de servicio |
| **Evidencias fotográficas** | Fotografías del vehículo tomadas al momento del ingreso para documentar su estado |
| **Google Drive** | Servicio de almacenamiento en la nube donde se guardan las fotografías cargadas en el sistema |
| **Estado "Por asignar"** | Estado inicial de una orden recién creada, indica que aún no tiene técnico asignado |
| **Motivo de ingreso** | Descripción breve del problema o servicio que solicita el cliente |
| **Persona que entrega** | Persona que lleva físicamente el vehículo al taller. Puede ser diferente al propietario |
| **Razón social** | Nombre legal y completo de una empresa tal como está registrado ante la autoridad tributaria |
| **NIT** | Número de Identificación Tributaria. Identificador único de una empresa ante la DIAN (Colombia) |
| **GNC** | Gas Natural Comprimido. Tipo de combustible alternativo a la gasolina |
| **GLP** | Gas Licuado de Petróleo (propano/butano). Tipo de combustible alternativo |
| **Nivel de combustible** | Indicador de la cantidad de combustible en el tanque al momento de recibir el vehículo |
| **Objetos de valor** | Pertenencias del cliente que se encuentran dentro del vehículo al momento del ingreso |
| **Campo obligatorio** | Campo marcado con un asterisco rojo (\*) que debe ser diligenciado para poder guardar la orden |

\newpage

---

*Manual de Usuario — Sistema de Taller de Autos*  
*Rol: Asesor de Recepción — Versión 1.0 — Junio 2026*  
*MegaTecnicentro*
