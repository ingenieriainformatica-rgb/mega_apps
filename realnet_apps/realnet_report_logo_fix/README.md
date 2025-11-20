# Realnet Report Logo Fix

## Descripción
Este módulo corrige el problema de visualización del logo de la compañía en los reportes PDF generados por Odoo. 

## Problema que resuelve
En Odoo, algunos reportes PDF no muestran el logo de la compañía correctamente debido a:
- Uso de `image_data_uri` que puede generar datos Base64 incorrectos o muy largos
- La variable `company` no siempre apunta a la compañía correcta del documento
- wkhtmltopdf tiene problemas procesando imágenes Base64 muy grandes

## Solución implementada
Este módulo hereda y modifica los layouts QWeb de reportes (`external_layout_bubble`, `external_layout_standard`, `external_layout_clean`, `external_layout_boxed`) para:

1. **Asegurar que la variable `company` apunte a la compañía del documento**: 
   - Si el objeto tiene `company_id` (facturas, pedidos, etc.), usa esa compañía
   - Si no, usa la variable `company` global

2. **Usar el endpoint `/web/image` en lugar de `image_data_uri`**:
   - Cambia de `t-att-src="image_data_uri(company.logo)"` 
   - A `t-att-src="'/web/image/res.company/%s/logo' % company.id"`
   - Esto genera una URL directa que wkhtmltopdf puede procesar sin problemas

3. **Establecer tamaño máximo para el logo**:
   - `max-height: 60px; max-width: 200px;`
   - Evita que el logo se renderice demasiado grande o pequeño

## Instalación

### 1. Actualizar lista de aplicaciones
En Odoo, ve a:
- **Aplicaciones** → Click en el menú de tres puntos (⋮) → **Actualizar lista de aplicaciones**

### 2. Buscar e instalar el módulo
- En el buscador de aplicaciones, escribe: `realnet_report_logo_fix`
- Click en **Instalar**

### 3. Reiniciar el servidor (opcional pero recomendado)
Si el módulo no aparece o tienes problemas, reinicia el servidor Odoo:
```powershell
# Detener el servidor
# Ctrl+C en la terminal donde corre Odoo

# Iniciar nuevamente
python odoo-bin -c odoo.conf
```

### 4. Actualizar módulo (si ya estaba instalado)
Si hiciste cambios en el código y el módulo ya estaba instalado:
```powershell
# En línea de comandos:
python odoo-bin -c odoo.conf -u realnet_report_logo_fix

# O desde la interfaz:
# Aplicaciones → buscar "realnet_report_logo_fix" → Click en "Actualizar"
```

## Verificación

### 1. Asegúrate de que la compañía tiene logo
- Ve a **Ajustes** → **Compañías** → selecciona tu compañía
- En la pestaña **General**, sube un logo en el campo **Logo de la compañía**
- **Guarda** los cambios

### 2. Genera un reporte PDF
Prueba generando cualquier reporte PDF, por ejemplo:
- Una factura: **Facturación** → **Facturas de cliente** → Abre una factura → **Imprimir** → **Factura**
- Un presupuesto: **Ventas** → **Presupuestos** → Abre un presupuesto → **Imprimir** → **Presupuesto**
- Un recibo de pago POS

### 3. Verifica el logo
- Abre el PDF generado
- El logo de la compañía debería aparecer en el encabezado del documento
- Prueba con diferentes layouts (Bubble, Standard, Clean, Boxed) desde **Ajustes** → **Compañías** → **Configuración del documento**

## Layouts soportados
- ✅ External Layout Bubble (`web.external_layout_bubble`)
- ✅ External Layout Standard (`web.external_layout_standard`)
- ✅ External Layout Clean (`web.external_layout_clean`)
- ✅ External Layout Boxed (`web.external_layout_boxed`)

## Dependencias
- `web` (módulo base de Odoo)

## Versión
- **Odoo**: 17.0
- **Módulo**: 1.0.0

## Autor
Realnet

## Licencia
LGPL-3

## Troubleshooting

### El logo no aparece
1. Verifica que la compañía tiene un logo subido
2. Verifica que el módulo está instalado: **Aplicaciones** → buscar "realnet_report_logo_fix" → debe mostrar "Instalado"
3. Actualiza el módulo: **Aplicaciones** → "realnet_report_logo_fix" → **Actualizar**
4. Limpia la caché del navegador
5. Verifica los logs de Odoo para ver si hay errores

### El logo aparece muy grande o muy pequeño
Puedes ajustar el tamaño editando el archivo `views/report_logo_fix.xml` y cambiando:
```xml
<attribute name="style">max-height: 60px; max-width: 200px;</attribute>
```

Ajusta los valores de `max-height` y `max-width` según tus necesidades.

### El módulo no aparece en la lista de aplicaciones
1. Verifica que la carpeta `realnet_report_logo_fix` está en `addons_realnet/`
2. Reinicia el servidor Odoo
3. Actualiza la lista de aplicaciones: **Aplicaciones** → menú (⋮) → **Actualizar lista de aplicaciones**
4. Verifica que la ruta `addons_realnet` está en el parámetro `addons_path` de tu archivo `odoo.conf`

## Notas técnicas

### ¿Por qué usar `/web/image` en lugar de `image_data_uri`?
- `image_data_uri` genera una cadena Base64 muy larga que puede causar problemas en wkhtmltopdf
- `/web/image` es un endpoint HTTP que devuelve la imagen directamente
- wkhtmltopdf maneja mejor URLs HTTP que datos Base64 embebidos
- Es más eficiente en términos de rendimiento y tamaño del HTML generado

### ¿Por qué `priority="999"`?
- Usamos prioridad alta (999) para asegurar que nuestras modificaciones se apliquen después de otras herencias
- Esto garantiza que nuestro fix tenga la última palabra en la definición del template

### ¿Qué hace `position="inside"`?
- Inyecta el código al inicio del template `web.external_layout`
- Esto asegura que la variable `company` se redefina antes de que se use en los sub-templates
