# Validación Secuencial de Documentos Soporte - Colombia

## 📋 Descripción

Módulo para Odoo 18 Enterprise que valida que los documentos soporte (facturas de compra electrónicas) se envíen a la DIAN en orden secuencial antes de permitir confirmar nuevos documentos.

## ✨ Características

- ✅ **Validación Automática**: Detecta cuando se intenta confirmar un documento soporte
- ✅ **Verificación de Estado DIAN**: Valida que el documento anterior esté enviado correctamente
- ✅ **Dos Modos de Operación**:
  - **Bloquear**: Impide confirmar si el anterior no está enviado
  - **Advertir**: Permite confirmar pero registra warning en logs
- ✅ **Bypass Manual**: Usuarios autorizados pueden omitir la validación en casos excepcionales
- ✅ **Integración Total**: Compatible con `l10n_co_dian` de Odoo Enterprise
- ✅ **Información Visual**: Tab dedicado en facturas con estado del documento anterior

## 📦 Requisitos

### Módulos Requeridos
- `account` (Odoo base)
- `l10n_co` (Localización Colombia)
- **`l10n_co_dian`** (Conexión directa DIAN - Odoo Enterprise) ⚠️ **CRÍTICO**

### Configuración Previa
1. Tener configurada la conexión con DIAN
2. Journals de compra configurados como documentos soporte:
   - Tipo: Compra
   - Resolución DIAN configurada (`l10n_co_edi_dian_authorization_number`)

## 🚀 Instalación

1. Copiar el módulo a la carpeta de addons de Odoo
2. Actualizar lista de aplicaciones
3. Buscar "Colombia - Validación Secuencial de Documentos Soporte"
4. Instalar el módulo

## ⚙️ Configuración

### Activar/Desactivar Validación

1. Ir a **Contabilidad → Configuración → Ajustes**
2. Buscar la sección **"Documentos Soporte (Colombia)"**
3. Activar **"Validar Secuencia de Documentos Soporte"**
4. Seleccionar el modo:
   - **Bloquear Confirmación**: Error si anterior no enviado
   - **Solo Advertir**: Warning en log pero permite confirmar

### Asignar Permisos de Bypass

Para permitir que un usuario pueda omitir la validación en casos excepcionales:

1. Ir a **Ajustes → Usuarios y Compañías → Usuarios**
2. Editar el usuario
3. En la pestaña **"Derechos de Acceso"**
4. Buscar y activar: **"Documento Soporte / Administrador de Validación"**

## 📖 Uso

### Flujo Normal

1. Usuario crea factura de compra (documento soporte)
2. Al confirmar, el sistema:
   - Detecta que es documento soporte
   - Busca el documento anterior en el mismo journal
   - Verifica el estado DIAN del anterior
3. Si el anterior está **Aceptado** o **Rechazado**: ✅ Permite confirmar
4. Si el anterior está **Pendiente** o **No enviado**: ❌ Bloquea (modo block) o ⚠️ Advierte (modo warn)

### Estados DIAN Válidos

| Estado | Comportamiento |
|--------|----------------|
| `invoice_accepted` | ✅ Permite confirmar siguiente documento |
| `invoice_rejected` | ✅ Permite confirmar (para no bloquear indefinidamente) |
| `invoice_pending` | ❌ Bloquea / ⚠️ Advierte (según configuración) |
| `invoice_sending_failed` | ❌ Bloquea / ⚠️ Advierte (según configuración) |
| Sin enviar (NULL) | ❌ Bloquea / ⚠️ Advierte (según configuración) |

### Usar Bypass Manual

Solo para usuarios autorizados:

1. Abrir el documento soporte en borrador
2. Ir al tab **"Validación Doc. Soporte"**
3. En la sección **"Bypass Manual de Validación"** (solo visible con permisos)
4. Activar **"Validación de Secuencia Anulada"**
5. Confirmar el documento

⚠️ **Importante**: El bypass queda registrado en logs para auditoría.

## 🔍 Información Técnica

### Campos Creados en `account.move`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `support_doc_validation_override` | Boolean | Permite bypass manual (solo con permisos) |
| `previous_support_doc_id` | Many2one | Referencia al documento anterior |
| `previous_support_doc_dian_state` | Selection | Estado DIAN del documento anterior |
| `show_support_doc_warning` | Boolean | Indica si mostrar alerta |

### Campos Creados en `res.company`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `support_doc_sequence_validation` | Boolean | Activar/desactivar validación |
| `support_doc_validation_mode` | Selection | Modo: 'block' o 'warn' |

### Campos Utilizados (Existentes)

De `l10n_co_edi`:
- `l10n_co_edi_is_support_document`: Identifica documento soporte

De `l10n_co_dian`:
- `l10n_co_dian_state`: Estado de envío a DIAN
- `l10n_co_dian_document_ids`: Documentos DIAN relacionados
- `l10n_co_edi_cufe_cude_ref`: CUFE/CUDE/CUDS

## 🧪 Testing

### Escenario 1: Primer Documento
- ✅ Debe permitir confirmar sin validación (no hay anterior)

### Escenario 2: Segundo Documento - Anterior Aceptado
- ✅ Debe permitir confirmar

### Escenario 3: Segundo Documento - Anterior Pendiente (Modo Block)
- ❌ Debe bloquear con error claro

### Escenario 4: Segundo Documento - Anterior Pendiente (Modo Warn)
- ⚠️ Debe permitir confirmar con warning en log

### Escenario 5: Bypass Manual
- ✅ Usuario con permisos puede confirmar activando bypass

## 📝 Logs

El módulo registra logs importantes en `/var/log/odoo/odoo-server.log`:

```
INFO: Documento anterior encontrado: DS0001 para DS0002
WARNING: Confirmación bloqueada para DS0002: anterior DS0001 no enviado
INFO: Bypass activado por Usuario Admin para documento DS0002
```

## 🐛 Solución de Problemas

### Error: "No se puede confirmar el documento soporte..."

**Causa**: El documento anterior no ha sido enviado a DIAN.

**Solución**:
1. Abrir el documento anterior
2. Usar botón "Enviar Documento Soporte a DIAN"
3. Esperar respuesta de DIAN
4. Intentar confirmar nuevamente

### La validación no se ejecuta

**Verificar**:
1. ¿El journal tiene `l10n_co_edi_dian_authorization_number` configurado?
2. ¿La validación está activa en Configuración?
3. ¿Es realmente un documento soporte (factura de compra con resolución)?

### No veo el tab "Validación Doc. Soporte"

**Causa**: Solo es visible para documentos soporte.

**Verificar**:
- El journal debe ser tipo "Compra"
- Debe tener resolución DIAN configurada
- Campo `l10n_co_edi_is_support_document` debe ser True

## 📞 Soporte

Para reportar bugs o solicitar mejoras, contactar al equipo de desarrollo.

## 📄 Licencia

LGPL-3

## 👥 Autores

- Implementado siguiendo plan validado con código fuente real de Odoo 18
- Basado en módulos `l10n_co_dian` y `l10n_co_edi`

---

**Versión**: 1.0.0
**Fecha**: Octubre 2025
**Compatible con**: Odoo 18.0 Enterprise
