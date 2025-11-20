# Realnet - Consecutivos Globales CE/CI para Pagos

Asigna de forma automática y única un consecutivo global CE/CI a los pagos al momento de su validación (posteo):
- Pagos salientes (outbound) ➜ CE
- Pagos entrantes (inbound) ➜ CI

El consecutivo CE/CI se muestra en las vistas de pago, en asientos contables relacionados y en los reportes PDF de recibos de pago y asientos.

## Características
- Campo único `x_ceci_number` (sólo lectura) en `account.payment`, con restricción de unicidad a nivel de base de datos.
- Campo `x_ceci_type` para indicar el tipo asignado: `ce` (outbound) o `ci` (inbound).
- Campos de compatibilidad no almacenados `x_ce_number` y `x_ci_number` para usos externos que esperen campos separados.
- Campo calculado `x_ceci_display` para mostrar en el título del formulario de pagos (muestra CE/CI si existe, de lo contrario el número interno).
- Asignación automática del consecutivo en `action_post` (tras postear exitosamente). No asigna para pagos de tipo `transfer`.
- Secuencias técnicas creadas:
  - `l10n_co.payment.ce` (prefijo CE)
  - `l10n_co.payment.ci` (prefijo CI)
  Ambas son globales (sin compañía) por defecto; si se crea una secuencia con el mismo `code` y `company_id`, se usará esa priorizando la de compañía.
- Vistas:
  - Lista de pagos: columna CE/CI visible y filtros por número y tipo.
  - Formulario de pagos: el título muestra CE/CI.
  - Formulario de asientos (`account.move`): para asientos tipo `entry` muestra el CE/CI cuando proviene de un pago relacionado.
- Reportes:
  - Recibo de pago: reemplaza el número interno por CE/CI cuando exista; también en la sección de pagos aplicados.
  - Asiento contable (plantilla de `custom_accounting_reports`): muestra CE/CI en el encabezado y en el nombre del archivo PDF.

## Flujo de funcionamiento
1. El usuario crea un pago y lo valida (postea).
2. El módulo determina el tipo (`outbound`/`inbound`) y toma la próxima secuencia CE o CI.
3. Se escribe de forma atómica el `x_ceci_number` y el `x_ceci_type` sobre el pago.
4. El número CE/CI se refleja en:
   - Título del pago y columna en la lista.
   - Título del asiento contable relacionado (cuando aplique).
   - PDF de recibo de pago y de asiento contable.

## Configuración
- Sin configuración obligatoria. Las secuencias CE y CI se crean con prefijos `CE`/`CI`, relleno 5 y numeración inicial 1.
- Para llevar series por compañía, cree secuencias con el mismo `code` (`l10n_co.payment.ce` y `l10n_co.payment.ci`) y defina `company_id`; el módulo las priorizará sobre la global.
- Si necesita reiniciar/ajustar la numeración, actualice el campo `number_next` de la secuencia correspondiente.

## Instalación
Requisitos:
- `account`
- `custom_accounting_reports` (para heredar la plantilla del reporte de asiento)

Pasos:
1. Actualice la lista de aplicaciones.
2. Instale “Realnet - Consecutivos Globales CE/CI Pagos Clientes y Proveedores”.

## Limitaciones y notas
- No asigna CE/CI a pagos de tipo `transfer` u otros distintos a `inbound`/`outbound`.
- Si las secuencias no existen o fueron eliminadas, al postear se lanzará un error pidiendo actualizar el módulo.
- La vista de lista de pagos se reemplaza para asegurar la visualización de CE/CI; esto puede entrar en conflicto con otras personalizaciones que también reemplacen la lista completa.

## Detalles técnicos
- Modelos extendidos: `account.payment`, `account.move`.
- Campos nuevos principales: `x_ceci_number` (único), `x_ceci_type`, `x_ceci_display`; de compatibilidad: `x_ce_number`, `x_ci_number`.
- Lógica de asignación: método privado `_assign_ceci_number_if_needed()` llamado tras `action_post()`.
- Detección del pago relacionado desde `account.move` usando `origin_payment_id`, `line_ids.payment_id` y enlaces de conciliación como respaldo.

## Versionado y licencia
- Versión del módulo: 18.0.2.0.0
- Licencia: OEEL-1 (según `__manifest__.py`).

## Créditos
Desarrollado por Realnet.
