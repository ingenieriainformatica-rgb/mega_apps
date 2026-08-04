# Mega - Table Sales Dashboard

Tablero comercial dinámico (`mega_sale_table_dashboard`) que muestra KPIs de
facturación, notas crédito, ventas por asesor y por cliente, agrupados por
sede (almacén) y diario contable, con comparación contra el período anterior.

Se accede desde **Contabilidad → Informes → Facturado**.

## ¿Qué muestra?

- **Banner de KPIs**: ventas con IVA, subtotal (base gravable), número de
  facturas, y los mismos indicadores para notas crédito.
- **Acordeón por sede**, y dentro de cada sede:
  - Resumen de facturado / notas crédito por diario.
  - Totales por **asesor** (campo `x_studio_concepto` de la factura).
  - Totales por **cliente** (NIT incluido).
  - Detalle de movimientos (facturas y NC) con acceso directo al documento
    haciendo clic en la fila.
- Comparación automática contra el **período anterior** de igual duración.

## Filtros

Barra de filtros con recarga automática (sin botón "Aplicar"):

- Rango de fechas (atajos: Hoy, Esta semana, Este mes, o rango personalizado
  con el datepicker nativo de Odoo).
- Sede (almacén).
- Diario de venta (se recalcula según la sede elegida).
- Asesor (contacto marcado como asesor).

## Configuración requerida

Para que una sede y sus diarios aparezcan en el tablero:

1. **Almacén** (`Inventario → Configuración → Almacenes`): activar el
   toggle **"Mostrar en informe (Tablero)"** (pestaña "Informes").
2. **Diario de venta** (`Contabilidad → Configuración → Diarios`): asociar
   el/los almacén(es) que facturan con ese diario en la pestaña
   **"Almacenes"** (campo `warehouse_ids`).
3. Solo se listan diarios de tipo `sale` vinculados a un almacén activo, y
   solo se muestran tarjetas de diario si tienen facturas o notas crédito
   en el período/filtro seleccionado.

> El campo "Asesor" depende de que el contacto tenga `is_advisor = True`
> (aportado por el módulo `mega_sale_advisor`) y de que las facturas tengan
> el campo `x_studio_concepto` diligenciado.

## Dependencias

- Módulos Odoo: `sale`, `web`, `account`, `stock`.
- Campos externos usados pero **no definidos** en este módulo (deben venir
  instalados por otro módulo, típicamente `mega_sale_advisor`):
  - `res.partner.is_advisor`
  - `account.move.x_studio_concepto`

## Estructura técnica (resumen)

- **Backend**: `controllers/controllers.py` expone rutas JSON bajo
  `/mega_dashboard/...`; la lógica de negocio vive en
  `controllers/services/sales.py` y `controllers/services/utils.py`.
- **Modelos**: extiende `stock.warehouse` (`show_in_sales_dashboard`) y
  `account.journal` (`warehouse_ids`).
- **Frontend**: componente OWL `MegaSaleDashboard`
  (`static/src/dashboard/tablero/sale_dashboard.js`), registrado como acción
  de cliente `realnet_sale_dashboard`, con un servicio reactivo
  `sales.statistics` (`static/src/dashboard/services_utils.js`) que centraliza
  el estado de filtros y la recarga de datos.

Ver [CONTEXT.md](CONTEXT.md) para el detalle de la arquitectura, el flujo de
datos y las notas para mantenimiento.
