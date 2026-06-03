# Duplicate Participants Check

Antes de actualizar `mega_colombia_jersey_landing` con la restriccion unica sobre
la cedula normalizada, revisa si existen participantes duplicados.

Esta consulta solo reporta duplicados; no modifica datos:

```sql
SELECT
    regexp_replace(vat, '\D', '', 'g') AS cedula_normalizada,
    COUNT(*) AS cantidad,
    array_agg(id ORDER BY id) AS participantes
FROM mega_jersey_contest_participant
GROUP BY regexp_replace(vat, '\D', '', 'g')
HAVING COUNT(*) > 1;
```

Si la consulta devuelve filas, resuelve los duplicados manualmente antes de
actualizar el modulo. No elimines registros sin confirmacion del responsable.
