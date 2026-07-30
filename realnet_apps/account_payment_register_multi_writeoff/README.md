# Payment Register - Multiple Writeoff Lines

## 📖 Descripción

Módulo para Odoo 18 Enterprise que permite agregar **múltiples líneas de writeoff** en el wizard de registro de pagos, cada una con su propia cuenta contable, monto y etiqueta.

---

## ✨ Características Principales

- ✅ Múltiples líneas de writeoff por pago
- ✅ Validación automática: suma = diferencia de pago
- ✅ Distribución analítica por línea
- ✅ Compatible con modo simple (backward compatibility)
- ✅ Botones de ayuda para operaciones rápidas
- ✅ Drag & drop para reordenar líneas

---

## 📋 Uso Rápido

1. Abrir factura → **"Registrar Pago"**
2. Modificar monto para crear diferencia
3. Seleccionar **"Mark as fully paid"**
4. Activar **"Use Multiple Writeoff Lines"**
5. Agregar líneas con diferentes cuentas y montos
6. Validar que la suma coincida con la diferencia
7. **"Create Payment"**

---

## 🔧 Instalación

```bash
# 1. Copiar módulo a addons
cp -r account_payment_register_multi_writeoff /path/to/odoo/addons/

# 2. Actualizar lista de módulos en Odoo
# Apps > Update Apps List

# 3. Instalar
# Apps > Buscar "Payment Register Multi Writeoff" > Install
```

---

## 📚 Documentación Completa

Ver [PLAN_IMPLEMENTACION.md](./PLAN_IMPLEMENTACION.md) para:
- Plan técnico detallado
- Arquitectura de la solución
- Guía de desarrollo paso a paso
- Tests unitarios
- Referencias de código

---

## 🎯 Ejemplo de Uso

**Caso:** Factura de $1,000 pero el cliente paga $950

**Distribución de la diferencia ($50):**
- $30 → Descuentos concedidos
- $15 → Comisiones bancarias
- $5 → Diferencias de cambio

---

## 🧪 Testing

```bash
# Ejecutar tests
odoo-bin -c odoo.conf -d test_db -i account_payment_register_multi_writeoff --test-enable
```

---

## 📄 Licencia

LGPL-3

## 👥 Autor

Realnet

## 📅 Versión

1.0.0 (2025-11-18)

---

## 🔗 Enlaces

- **Documentación Técnica:** [PLAN_IMPLEMENTACION.md](./PLAN_IMPLEMENTACION.md)
- **Soporte:** gerencia@realnet.com.co
