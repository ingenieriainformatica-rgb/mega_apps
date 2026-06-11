# Mega CRM Lost Reason on Fold Stage

Modulo para Odoo 18 que obliga a capturar motivo de perdida y nota de cierre
antes de mover una oportunidad (`crm.lead`) a una etapa final/rechazada.

## Deteccion de etapa rechazada/final

La etapa se considera rechazada/final cuando:

- `crm.stage.fold = True`
- `crm.stage.is_won = False`

Odoo 18 trae el campo estandar `is_won` en `crm.stage`, por eso se usa para
excluir la etapa Ganado.

## Interfaz

El modulo intercepta:

- Arrastre en kanban CRM agrupado por `stage_id`.
- Cambio de etapa desde el statusbar del formulario CRM.

Si la etapa destino es folded/no ganada, cancela el cambio normal y abre el
wizard `mega.crm.lost.stage.reason.wizard`.

## Backend

`crm.lead.write()` bloquea cualquier escritura directa de `stage_id` hacia una
etapa folded/no ganada si no viene el contexto `skip_lost_stage_validation=True`.
El wizard usa ese contexto despues de exigir motivo y nota.

## Wizard estandar

El wizard estandar `crm.lead.lost` usa el campo `lost_feedback` para la nota de
cierre. Este modulo lo hereda para exigir motivo y nota tambien al usar el boton
estandar "Marcar como perdido".
