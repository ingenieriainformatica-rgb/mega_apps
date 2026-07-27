# Mega Aged Receivable - Customer Column in XLSX

Módulo de Odoo 18 Enterprise que agrega, solo en una descarga Excel dedicada del informe **Cuenta por Cobrar Vencida** (Aged Receivable, `/odoo/aged-receivable`), tres columnas que el informe estándar no trae: **Cliente**, **NIT** y **Fecha del documento**, repetidas en cada fila de factura/pago/nota, no solo en el encabezado del grupo.

## Qué hace el módulo

En el informe nativo, el nombre del cliente solo aparece como título de la fila plegable ("ADELANTE SOLUCIONES FINANCIERAS S.A.S. ▾"); nunca se repite en cada factura de detalle, lo que hace imposible filtrar, ordenar o analizar el Excel por cliente. Este módulo:

1. Agrega una entrada nueva al menú del engranaje (⚙) del informe, junto a "Copiar a Documentos": **"XLSX con Cliente, NIT y Fecha por fila"**.
2. Esa descarga incluye, además de todas las columnas estándar (Fecha de factura, A la fecha, 1-30, 31-60, 61-90, 91-120, Antiguos, Total):
   - **Cliente**: nombre del cliente real del documento (factura, nota crédito, pago manual, anticipo, apunte contable), repetido en cada fila.
   - **NIT**: identificación tributaria del mismo cliente.
   - **Fecha del documento**: fecha contable del apunte, incluso para pagos y otros movimientos que no tienen "Fecha de factura" (ese campo estándar solo existe en facturas).
3. El botón **XLSX** estándar, el **PDF**, y la tabla interactiva del informe quedan exactamente como el core de Odoo los define — ninguno de los tres muestra estas columnas nuevas.

## Por qué el cliente no aparecía y por qué "Cliente" a veces no coincidía con la factura

El motor del reporte agrupa por `account_move_line.partner_id` (el socio del apunte contable), pero ese campo puede estar desalineado del cliente real de la factura (`account_move.partner_id`, lo que se ve al abrir el documento) — se detectó un caso real donde el apunte contable de una factura tenía un cliente distinto al de la factura misma. Por eso, **Cliente** y **NIT** se calculan siempre a partir de `account_move_line.move_id.partner_id.commercial_partner_id` (el cliente real del documento, resuelto a su empresa matriz si es un contacto hijo), no del `partner_id` crudo del apunte.

## Cómo usarlo

1. Abrir **Contabilidad → Informes → Cuenta por cobrar vencida**.
2. Ajustar la fecha de corte, filtros de cliente/compañía como siempre.
3. Clic en el engranaje (⚙) junto al título del informe.
4. Elegir **"XLSX con Cliente, NIT y Fecha por fila"**.
5. Se descarga un `.xlsx` con las columnas nuevas ya incluidas, listo para filtrar/ordenar por cliente en Excel.

El botón **XLSX** de la barra de herramientas sigue funcionando igual que siempre, sin estas columnas.

## Dependencias

- `account`
- `account_reports`

## Estructura del código

```text
mega_aged_receivable_customer_xlsx/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── account_report.py                 # botón nuevo en el menú engranaje + método de descarga
│   └── account_aged_partner_balance.py    # cálculo de Cliente/NIT/Fecha del documento
├── data/
│   └── aged_receivable_customer_column.xml  # columnas y expresiones nuevas del reporte
└── tests/
    ├── __init__.py
    └── test_aged_receivable_customer_xlsx.py  # 25 tests automatizados
```

## Arquitectura (resumen técnico)

- **`data/aged_receivable_customer_column.xml`**: declara 3 `account.report.column` + 3 `account.report.expression` nuevas sobre el reporte existente `account_reports.aged_receivable_report`, reutilizando el motor de cómputo estándar (`_report_custom_engine_aged_receivable`) — no se duplica SQL.
- **`models/account_aged_partner_balance.py`**: hereda `account.aged.partner.balance.report.handler` (el handler compartido por Aged Receivable y Aged Payable) y enriquece, en un solo lote por página (no una consulta por fila), el resultado ya calculado por el core con `partner_name`, `partner_vat` y `document_date`.
- **`models/account_report.py`**: agrega la entrada al menú engranaje (`_init_options_buttons`) y el método de descarga dedicado. Las columnas nuevas solo se activan mediante un **contexto de la petición** (`with_context(mega_show_partner_name_column=True)`), nunca mediante un valor guardado en las opciones del reporte — así se evita que la columna "se quede pegada" en pantalla después de una descarga (bug real detectado y corregido durante el desarrollo).
- No se modificó ningún archivo de `account`, `account_reports`, ni ningún otro módulo.

## Pruebas

25 tests automatizados (`tests/test_aged_receivable_customer_xlsx.py`), cubriendo: múltiples facturas por cliente, dos clientes distintos, factura parcialmente pagada, nota crédito, pago sin conciliar, apunte sin cliente, contacto hijo, cliente sin NIT, totales Odoo vs Excel, filtros de fecha/cliente/compañía, y que la tabla interactiva, el PDF y el botón XLSX estándar permanezcan intactos.

## Autoría

Módulo desarrollado por **Jorge Alberto Quiroz Sierra** para MegaTecnicentro.
