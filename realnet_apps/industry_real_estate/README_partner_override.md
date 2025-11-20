# Funcionalidad: Conservar Partner Manual en Líneas Contables

## Descripción

Esta funcionalidad permite que cuando un usuario cambia manualmente el campo "Contacto" (partner_id) en las líneas contables de una factura (tab "Apuntes contables" / "Journal Items"), el valor seleccionado se conserve al confirmar la factura, en lugar de ser reemplazado automáticamente por el cliente de la factura.

## Problema Original

En Odoo 18 estándar, el comportamiento es:

1. Usuario crea una factura con Cliente = "Deco Addict"
2. Usuario entra al tab "Apuntes contables" (Journal Items)
3. Usuario cambia el Contacto de una línea a "Gemini Furniture"
4. Usuario confirma la factura
5. ❌ **PROBLEMA**: Odoo recalcula automáticamente el partner_id y lo reemplaza por "Deco Addict"

## Solución Implementada

Se agregó un campo técnico `partner_id_manual_override` que marca cuando el usuario ha cambiado manualmente el partner_id, evitando que sea recalculado.

### Flujo de la Solución

1. Usuario crea una factura con Cliente = "Deco Addict"
2. Usuario entra al tab "Apuntes contables" (Journal Items)
3. Usuario cambia el Contacto de una línea a "Gemini Furniture"
   - ✅ Se activa `partner_id_manual_override = True` en esa línea
4. Usuario confirma la factura
5. ✅ **SOLUCIÓN**: El método `_compute_partner_id` detecta el flag y NO recalcula el partner
6. El contacto "Gemini Furniture" se conserva

## Archivos Modificados/Creados

### 1. Modelo Python
**Archivo**: `models/account_move_line.py`

```python
class AccountMoveLineInherit(models.Model):
    _inherit = 'account.move.line'

    partner_id_manual_override = fields.Boolean(...)

    def _compute_partner_id(self):
        # Respeta cambios manuales
        for line in self:
            if not line.partner_id_manual_override:
                line.partner_id = line.move_id.partner_id.commercial_partner_id

    def _inverse_partner_id(self):
        # Marca cuando se cambia manualmente
        ...
```

### 2. Vista XML
**Archivo**: `views/account_move_inherit_views.xml`

- Hace visible la columna "Contacto" en el tab Journal Items
- Agrega el campo técnico `partner_id_manual_override` (invisible)

### 3. Definición de Campo
**Archivo**: `data/account_move_line_fields.xml`

- Define el campo técnico en `ir.model.fields`

### 4. Registro en __init__.py
```python
from . import account_move_line
```

### 5. Registro en __manifest__.py
```python
'data/account_move_line_fields.xml',
```

## Casos de Uso

### Caso 1: Cambio Manual Simple
```
Factura: Cliente = "Deco Addict"
Línea 1: Cuenta 281500, Contacto = "Deco Addict" (automático)
↓ Usuario cambia manualmente
Línea 1: Cuenta 281500, Contacto = "Gemini Furniture"
↓ Se confirma la factura
Línea 1: Cuenta 281500, Contacto = "Gemini Furniture" ✅ (conservado)
```

### Caso 2: Restablecer al Original
```
Línea 1: Contacto = "Gemini Furniture" (manual_override = True)
↓ Usuario vuelve a cambiar al original
Línea 1: Contacto = "Deco Addict"
↓ Sistema detecta que coincide con el move
Línea 1: manual_override = False ✅ (se quita el flag)
```

### Caso 3: Nuevas Líneas
```
Se agregan nuevas líneas después del cambio manual
↓
Nuevas líneas: Contacto = "Deco Addict" (comportamiento estándar) ✅
Línea modificada: Contacto = "Gemini Furniture" (conservado) ✅
```

## Métodos Sobreescritos

| Método | Propósito |
|--------|-----------|
| `_compute_partner_id()` | Calcula el partner_id respetando cambios manuales |
| `_inverse_partner_id()` | Marca el flag cuando se cambia manualmente |
| `create()` | Detecta override en creación de líneas |
| `write()` | Detecta override en modificación de líneas |

## Instalación/Actualización

Para aplicar esta funcionalidad:

```bash
# Actualizar el módulo
odoo-bin -u industry_real_estate -d tu_base_de_datos

# O reiniciar con auto-reload
```

## Compatibilidad

- ✅ Odoo 18 Enterprise
- ✅ Compatible con módulo `account`
- ✅ No modifica código core de Odoo
- ✅ Usa herencia estándar de Odoo

## Notas Técnicas

1. El campo `partner_id_manual_override` NO se copia (`copy=False`)
2. El campo es técnico y no se muestra al usuario final
3. La lógica es reversible: si vuelves a poner el partner original, el flag se desactiva
4. Compatible con importaciones masivas y API

## Autor

Realnet - 2025
