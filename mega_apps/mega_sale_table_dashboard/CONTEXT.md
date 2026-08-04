# CONTEXT.md — mega_sale_table_dashboard

Notas técnicas para quien mantenga este módulo. El README.md cubre el "qué
hace"; este documento cubre el "cómo funciona por dentro" y las trampas
conocidas.

## Flujo de datos end-to-end

1. El usuario abre el menú **Informes → Facturado**
   ([views/sale_dashboard_menu.xml](views/sale_dashboard_menu.xml)), que
   dispara la acción de cliente `realnet_sale_dashboard`.
2. `MegaSaleDashboard`
   ([static/src/dashboard/tablero/sale_dashboard.js](static/src/dashboard/tablero/sale_dashboard.js))
   monta y:
   - Carga sedes (`/mega_dashboard/get/warehouses`) y asesores
     (`/mega_dashboard/get/advisors`).
   - Dispara `_autoLoad()`, que llama al servicio `sales.statistics` con el
     mes actual y todos los filtros en modo "todos" (`allHeadquarters`,
     `allJournal`, `allAdvisors`).
3. El servicio reactivo `sales.statistics`
   ([static/src/dashboard/services_utils.js](static/src/dashboard/services_utils.js))
   centraliza `date_from/date_to/warehouse_id/journal_id/advisor_id` y hace
   el RPC a `/mega_dashboard/sales/statistics`. Todo el árbol de componentes
   lee de este único estado reactivo (no hay props "prop drilling" del
   resultado).
4. El controlador Python
   ([controllers/controllers.py](controllers/controllers.py)) delega en
   `get_sales_data()`
   ([controllers/services/sales.py](controllers/services/sales.py)), que:
   - Normaliza los tokens `"allHeadquarters"/"allJournal"/"allAdvisors"` a
     `None` (`_norm_id`, `_resolve_advisor_name`).
   - Resuelve sedes activas y diarios de venta asociados.
   - Corre 3 pasadas sobre `account.move` (facturas `out_invoice` y notas
     crédito `out_refund`, con signo invertido en NC): KPIs agrupados por
     (sede, diario), totales por concepto/asesor, totales por cliente.
   - Calcula el período anterior de igual duración
     (`_get_previous_period_dates`) con `read_group` (rápido, sin cargar
     recordsets) para la comparación.
   - Descarta diarios sin facturas ni NC en el período (evita tarjetas
     vacías) y sedes sin diarios con datos.

## Regla de mapeo sede ↔ diario

`account.journal.warehouse_ids` es Many2many, pero el backend asume
**1 diario → 1 sede** en la práctica: en `_get_kpis_grouped` y en los
totales por concepto/cliente se toma **la primera** sede del diario
(`wh_ids[0]` / `(...ids or [None])[0]`). Si algún diario llega a asociarse a
más de una sede, los movimientos se atribuirán solo a la primera y el
tablero quedará inconsistente con la realidad contable. Si se necesita
soportar N:M de verdad, hay que revisar `_get_kpis_grouped`,
`_get_concept_totals_grouped` y `_get_partner_totals_grouped` en
[sales.py](controllers/services/sales.py).

## Dependencias implícitas no declaradas en el manifest

El `__manifest__.py` solo declara `sale, web, account, stock`, pero el
backend usa campos que **no pertenecen a este módulo**:

- `res.partner.is_advisor` → viene de `mega_sale_advisor`.
- `account.move.x_studio_concepto` → campo tipo Studio, usado también por
  `mega_sale_advisor`, `mega_concepto_show_list_factura`,
  `mega_invoice_report_concept`, `mega_account_concept_readonly_posted`.

Si `mega_sale_advisor` no está instalado, `get_advisors()`
([controllers/services/utils.py](controllers/services/utils.py)) fallará al
buscar por `is_advisor` (campo inexistente) o, si el campo Studio no existe,
`getattr(mv, "x_studio_concepto", "")` en `sales.py` degradará
silenciosamente a cadena vacía (no rompe, pero el desglose por asesor queda
vacío). **Antes de instalar este módulo en una BD nueva, verificar que
`mega_sale_advisor` (o el campo Studio equivalente) ya exista.**

## Seguridad

- Todas las rutas usan `auth="user"` + `sudo()` en las queries — **cualquier
  usuario interno autenticado** puede leer cifras de ventas/facturación de
  toda la compañía, sin importar sus grupos de Ventas/Contabilidad. No hay
  `ir.rule` ni chequeo de grupo adicional.
- No hay archivo `security/ir.model.access.csv` porque el módulo no define
  modelos nuevos (solo extiende `stock.warehouse` y `account.journal`, cuyos
  permisos ya existen).
- Si en algún momento se requiere restringir el acceso al tablero, el punto
  natural es añadir una validación de grupo al inicio de cada método en
  `controllers/controllers.py`, o mover las queries fuera de `sudo()` según
  el grupo del usuario.

## Código legacy / no usado (limpiar con cuidado)

El asset glob del manifest carga **todo** `static/src/dashboard/**/*`, así
que estos archivos se compilan y sirven aunque no estén conectados al árbol
de componentes activo (`MegaSaleDashboard` → `Layout`, `DateFilterBar`,
`KpiBanner`, `KpiBannerSkeleton` — ver
[tablero.xml](static/src/dashboard/tablero/tablero.xml)):

- `static/src/dashboard/xml/sale_dashboard.xml` — plantilla antigua
  `t-name="realnet_sale_dashboard.SaleDashboard"` (nombre distinto a la
  activa `mega_dashboard.SaleDashboard`), de una iteración anterior del
  tablero con un layout HTML plano (input `type="date"` en vez del
  datepicker nativo).
- `static/src/dashboard/informe/` (`Informe`), `static/src/dashboard/advisor/`
  (`Advisor`), `static/src/dashboard/InvoiceList/` (`InvoiceList`) y
  `static/src/dashboard/hero/` — componentes OWL exportados pero sin
  ninguna referencia en `tablero.xml` ni en `sale_dashboard.js`. Todo el
  desglose de asesores/clientes/movimientos que hoy se ve en el tablero está
  inline en `tablero.xml`, no usa estos componentes.

Antes de borrarlos, confirmar con `grep` que ningún otro módulo de
`mega_apps` los importa (no debería, son módulos OWL con nombres de
template propios).

## Tests

`tests/` solo contiene `__pycache__` (sin `.py` fuente ni `__init__.py`
registrando el paquete) — a pesar de que el historial de commits menciona
`test_advisor`, `test_journal_warehouse`, `test_kpis`,
`test_pagination_export`, `test_security`, `test_studio_field`
(deducido de los `.pyc` cacheados). Si se van a restaurar, hay que:
1. Recrear los `.py` fuente (los `.pyc` en `__pycache__` no son fiables como
   fuente — corresponden a una versión pasada del código y pueden no
   coincidir con el estado actual de `sales.py`/`utils.py`).
2. Agregar `tests/__init__.py` importando los módulos de test.
3. Agregar `from . import tests` en el `__init__.py` raíz si no está.

## Rutas HTTP expuestas

| Ruta | Tipo | Descripción |
|---|---|---|
| `/mega_dashboard/sales/statistics` | JSON | Payload completo del tablero (KPIs, grupos, período anterior) |
| `/mega_dashboard/get/advisors` | JSON | Lista de contactos con `is_advisor=True` |
| `/mega_dashboard/get/warehouses` | JSON | Sedes con `show_in_sales_dashboard=True` y al menos un diario de venta asociado |
| `/mega_dashboard/get/journals` | JSON | Diarios de venta de una sede (o de todas las sedes activas) |
