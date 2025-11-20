# Colombian POS - CUFE on Receipt

## Descripción

Módulo para Odoo 18 Enterprise que agrega el **CUFE** (Código Único de Factura Electrónica) y un **código QR** a la tirilla del punto de venta para Colombia.

## Características

✅ **Muestra el CUFE en la tirilla**: Cuando una orden del POS tiene una factura electrónica aceptada por la DIAN, el CUFE se muestra automáticamente en la tirilla.

✅ **Código QR del CUFE**: Se genera un código QR con el CUFE para facilitar la verificación de la factura.

✅ **Configurable**: Puedes habilitar/deshabilitar la visualización del CUFE por punto de venta.

✅ **Facturación automática opcional**: Opción para generar y enviar la factura a DIAN automáticamente al finalizar la orden.

## Dependencias

Este módulo requiere los siguientes módulos instalados:

- `l10n_co_pos` - Localización colombiana para POS
- `l10n_co_dian` - Facturación electrónica DIAN
- `point_of_sale` - Punto de venta de Odoo

## Instalación

1. Copia la carpeta `l10n_co_pos_receipt_cufe` en tu directorio de addons de Odoo
2. Actualiza la lista de aplicaciones:
   - Ir a Aplicaciones
   - Click en "Actualizar lista de aplicaciones"
3. Busca "Colombian POS - CUFE on Receipt"
4. Click en "Instalar"

## Configuración

### Configurar el Punto de Venta

1. Ve a **Punto de Venta > Configuración > Ajustes**
2. Selecciona tu punto de venta
3. En la sección **Facturación**, encontrarás dos nuevas opciones:

#### Mostrar CUFE en Tirilla
- **Activado** (predeterminado): Muestra el CUFE y QR en la tirilla cuando la factura está aceptada
- **Desactivado**: No muestra el CUFE en la tirilla

#### Facturar automáticamente en POS
- **Activado**: Genera y envía la factura a DIAN automáticamente al pagar la orden
- **Desactivado** (predeterminado): La facturación es manual

⚠️ **Importante**: La facturación automática requiere que tengas configurada la conexión con DIAN en producción.

## Uso

### Flujo Estándar (Facturación Manual)

1. **Crear orden en el POS**
   - Agrega productos
   - Finaliza la orden y cobra

2. **Generar factura**
   - Ve a Punto de Venta > Órdenes > Órdenes
   - Selecciona la orden
   - Click en "Factura"
   - Confirma la factura

3. **Enviar a DIAN**
   - En la factura, click en "Enviar a DIAN"
   - Espera la confirmación de aceptación

4. **Reimprimir la tirilla**
   - Ve a la orden del POS
   - Click en "Imprimir recibo"
   - **El CUFE y el QR ahora aparecerán en la tirilla**

### Flujo con Facturación Automática

Si tienes habilitada la facturación automática:

1. **Crear orden en el POS**
   - Agrega productos
   - Marca "Facturar" antes de pagar
   - Finaliza la orden y cobra

2. **Automático**
   - La factura se genera automáticamente
   - Se envía a DIAN automáticamente
   - El CUFE se muestra en la tirilla si fue aceptada

## Estructura de la Tirilla

Cuando una orden tiene factura aceptada, la tirilla mostrará:

```
[... productos y totales ...]

Order 00001-001-0001

--------------------------------
  FACTURA ELECTRÓNICA DIAN
--------------------------------

      [CÓDIGO QR DEL CUFE]

CUFE:
9d4d566dde824668016bae2f57834e3f
4f73f5b2c5e0b4d8f6a71c94d23a8b5c

Factura electrónica validada por la DIAN

--------------------------------

[... información de pie de página ...]
```

## Preguntas Frecuentes

### ¿Por qué no aparece el CUFE en mi tirilla?

El CUFE solo aparece si:
1. La orden tiene una factura asociada
2. La factura fue enviada a DIAN
3. La DIAN aceptó la factura (`estado = Aceptada`)
4. La opción "Mostrar CUFE en Tirilla" está activada en la configuración del POS

### ¿Puedo usar esto sin estar conectado a DIAN?

Sí, el módulo funciona en **modo demo** de DIAN. La factura se valida localmente y el CUFE se genera, pero no se envía realmente a DIAN.

### ¿El QR contiene toda la información de la factura?

No, el QR solo contiene el **CUFE** (el identificador único de la factura). Para obtener todos los detalles fiscales del QR según normativa DIAN, estos se generan en el reporte PDF de la factura, no en la tirilla del POS.

### ¿Puedo personalizar el diseño de la sección CUFE?

Sí, puedes modificar el archivo:
```
l10n_co_pos_receipt_cufe/static/src/overrides/components/order_receipt/order_receipt.xml
```

### ¿Cómo desactivo la facturación automática?

Ve a **Punto de Venta > Configuración > Ajustes** y desactiva la opción "Facturar automáticamente en POS".

## Soporte Técnico

Para reportar problemas o solicitar nuevas características:
- Email: soporte@realnet.com.co
- Web: https://www.realnet.com.co

## Licencia

LGPL-3

## Autor

Realnet - Soluciones Tecnológicas
https://www.realnet.com.co

## Versión

1.0.0 - Compatible con Odoo 18 Enterprise
