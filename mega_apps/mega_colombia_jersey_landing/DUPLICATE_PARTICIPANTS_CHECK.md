# Duplicate Participants Check

Antes de actualizar `mega_colombia_jersey_landing`, esta consulta permite revisar
si existen participantes historicos duplicados por la combinacion cedula
normalizada + placa normalizada.

La validacion del modulo se hace en Python/controlador y no requiere borrar
duplicados historicos para actualizar.

Esta consulta solo reporta duplicados; no modifica datos:

```sql
SELECT
    regexp_replace(vat, '\D', '', 'g') AS cedula_normalizada,
    upper(regexp_replace(license_plate, '[^A-Za-z0-9]', '', 'g')) AS placa_normalizada,
    COUNT(*) AS cantidad,
    array_agg(id ORDER BY id) AS participantes
FROM mega_jersey_contest_participant
GROUP BY
    regexp_replace(vat, '\D', '', 'g'),
    upper(regexp_replace(license_plate, '[^A-Za-z0-9]', '', 'g'))
HAVING COUNT(*) > 1;
```

Si la consulta devuelve filas, resuelve los duplicados manualmente antes de
actualizar el modulo. No elimines registros sin confirmacion del responsable.
