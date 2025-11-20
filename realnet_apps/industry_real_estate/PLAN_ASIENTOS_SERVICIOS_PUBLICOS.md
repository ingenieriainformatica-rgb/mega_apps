# Plan de Implementación: Asientos Contables Automáticos de Servicios Públicos

## Información del Proyecto
- **Módulo:** `industry_real_estate` (ECO-ERP)
- **Versión Odoo:** 18 Enterprise
- **Fecha:** 2025-10-29
- **Desarrollador:** Senior Odoo Developer

---

## Resumen Ejecutivo

Implementar la generación automática de asientos contables para cobro de servicios públicos y otros conceptos asociados a contratos de arrendamiento, integrándose con el método existente `_cron_generate_mandates_and_invoices`.

---

## Objetivos

1. Crear configuración de cuentas contables para conceptos faltantes
2. Implementar lógica de generación de asientos contables automáticos
3. Integrar con el cron existente de generación de documentos
4. Validar duplicados y manejar excepciones
5. Crear/obtener diario contable "COBRO DE OTROS CONCEPTOS"

---

## Alcance Funcional

### Conceptos a Cobrar

| # | Concepto | Campo Validación | Origen del Monto | Prorrateo Propietarios |
|---|----------|-----------------|------------------|----------------------|
| 1 | **Agua** | `servicios_publicos` | `x.meter.reading` (meter_type='water') | SÍ |
| 2 | **Energía** | `servicios_publicos` | `x.meter.reading` (meter_type='energy') | SÍ |
| 3 | **Saneamiento** | `servicios_publicos` | `x.meter.reading` (meter_type='sanitation') | SÍ |
| 4 | **Internet** | `internet` | `sale.order.monto_internet` | SÍ |
| 5 | **TV Cable** | `tv` | `sale.order.monto_tv` | SÍ |
| 6 | **Administración Sostenimiento** | `administracion_sostenimiento` | `sale.order.monto_administracion_sostenimiento` | SÍ |
| 7 | **Costo Transacción** | `costo_transaccion` | `sale.order.costo_transaccion_monto` | **NO** (especial) |

### Lógica Contable

#### Para Conceptos 1-6 (Con Prorrateo):
```
LÍNEAS CRÉDITO (por cada propietario):
- Partner: owner_id (de account.analytic.account.owner.line)
- Cuenta: utility_XXX_account_credit_id
- Monto: valor_concepto × (participation_percent / 100)

LÍNEA DÉBITO (única):
- Partner: partner_id (arrendatario del contrato)
- Cuenta: utility_XXX_account_debit_id
- Monto: valor_concepto (100%)
```

#### Para Concepto 7 (Costo Transacción - SIN Prorrateo):
```
LÍNEA CRÉDITO:
- Partner: partner_id (arrendatario)
- Cuenta: utility_transaction_cost_account_credit_id
- Monto: costo_transaccion_monto

LÍNEA DÉBITO:
- Partner: partner_id (arrendatario)
- Cuenta: utility_transaction_cost_account_debit_id
- Monto: costo_transaccion_monto
```

---

## Arquitectura de la Solución

### Modelos Afectados

1. **res.company** - Agregar cuentas contables faltantes
2. **res.config.settings** - Exponer configuración en UI
3. **sale.order** - Nuevo método de generación de asientos
4. **account.journal** - Crear/obtener diario "COBRO DE OTROS CONCEPTOS"

### Flujo de Ejecución

```
_cron_generate_mandates_and_invoices()
    ↓
    Para cada contrato (state='sale'):
        ↓
        _generate_all_documents_for_period()  [EXISTENTE]
        ↓
        _generate_utility_accounting_entries()  [NUEVO]
            ↓
            1. Validar duplicados (buscar asientos previos)
            2. Obtener mes actual (YYYY-MM)
            3. Validar campos booleanos activos
            4. Para cada concepto habilitado:
               a. Obtener valor (lectura o monto fijo)
               b. Validar existencia de cuentas
               c. Obtener propietarios con participation_percent
               d. Construir líneas débito/crédito
            5. Crear asiento contable unificado
            6. Publicar asiento (action_post)
```

---

## FASE 1: Configuración de Cuentas Contables

### 1.1 Modificar `res_company.py`

**Archivo:** `c:\odoo-dev-bancasa\addons_realnet\industry_real_estate\models\res_company.py`

**Agregar campos (después de línea 302):**

```python
# ADMINISTRACIÓN SOSTENIMIENTO
utility_admin_sostenimiento_account_debit_id = fields.Many2one(
    'account.account',
    string="Cuenta Débito - Administración Sostenimiento",
    domain="[('deprecated', '=', False), ('company_id', '=', id)]"
)

utility_admin_sostenimiento_account_credit_id = fields.Many2one(
    'account.account',
    string="Cuenta Crédito - Administración Sostenimiento",
    domain="[('deprecated', '=', False), ('company_id', '=', id)]"
)

# COSTO TRANSACCIÓN
utility_transaction_cost_account_debit_id = fields.Many2one(
    'account.account',
    string="Cuenta Débito - Costo Transacción",
    domain="[('deprecated', '=', False), ('company_id', '=', id)]"
)

utility_transaction_cost_account_credit_id = fields.Many2one(
    'account.account',
    string="Cuenta Crédito - Costo Transacción",
    domain="[('deprecated', '=', False), ('company_id', '=', id)]"
)
```

### 1.2 Modificar `res_config_settings.py`

**Archivo:** `c:\odoo-dev-bancasa\addons_realnet\industry_real_estate\models\res_config_settings.py`

**Agregar campos (después de línea 302):**

```python
# ADMINISTRACIÓN SOSTENIMIENTO
utility_admin_sostenimiento_account_debit_id = fields.Many2one(
    'account.account',
    related='company_id.utility_admin_sostenimiento_account_debit_id',
    readonly=False
)

utility_admin_sostenimiento_account_credit_id = fields.Many2one(
    'account.account',
    related='company_id.utility_admin_sostenimiento_account_credit_id',
    readonly=False
)

# COSTO TRANSACCIÓN
utility_transaction_cost_account_debit_id = fields.Many2one(
    'account.account',
    related='company_id.utility_transaction_cost_account_debit_id',
    readonly=False
)

utility_transaction_cost_account_credit_id = fields.Many2one(
    'account.account',
    related='company_id.utility_transaction_cost_account_credit_id',
    readonly=False
)
```

### 1.3 Actualizar Vista de Configuración

**Archivo:** `c:\odoo-dev-bancasa\addons_realnet\industry_real_estate\views\res_config_settings_views.xml`

**Agregar en la sección de cuentas contables:**

```xml
<!-- Administración Sostenimiento -->
<div class="col-12 col-lg-6 o_setting_box">
    <div class="o_setting_left_pane"/>
    <div class="o_setting_right_pane">
        <label for="utility_admin_sostenimiento_account_debit_id" string="Administración Sostenimiento - Débito"/>
        <field name="utility_admin_sostenimiento_account_debit_id"/>
        <label for="utility_admin_sostenimiento_account_credit_id" string="Administración Sostenimiento - Crédito"/>
        <field name="utility_admin_sostenimiento_account_credit_id"/>
    </div>
</div>

<!-- Costo Transacción -->
<div class="col-12 col-lg-6 o_setting_box">
    <div class="o_setting_left_pane"/>
    <div class="o_setting_right_pane">
        <label for="utility_transaction_cost_account_debit_id" string="Costo Transacción - Débito"/>
        <field name="utility_transaction_cost_account_debit_id"/>
        <label for="utility_transaction_cost_account_credit_id" string="Costo Transacción - Crédito"/>
        <field name="utility_transaction_cost_account_credit_id"/>
    </div>
</div>
```

**Resultado Esperado:**
- ✅ 4 nuevos campos en `res.company`
- ✅ 4 nuevos campos relacionados en `res.config.settings`
- ✅ Configuración visible en Ajustes → Industry Real Estate

---

## FASE 2: Lógica de Generación de Asientos

### 2.1 Crear Método Helper: `_get_or_create_utility_journal()`

**Archivo:** `c:\odoo-dev-bancasa\addons_realnet\industry_real_estate\models\sale_order.py`

**Ubicación:** Agregar después del método `_ecoerp_apply_dian_fields_on_vals` (~línea 1500)

```python
def _get_or_create_utility_journal(self):
    """
    Obtiene o crea el diario contable para cobro de servicios públicos.

    Returns:
        account.journal: Diario "COBRO DE OTROS CONCEPTOS" (tipo varios, código OTC)
    """
    journal = self.env['account.journal'].search([
        ('code', '=', 'OTC'),
        ('type', '=', 'general')
    ], limit=1)

    if not journal:
        journal = self.env['account.journal'].create({
            'name': 'COBRO DE OTROS CONCEPTOS',
            'code': 'OTC',
            'type': 'general',
            'show_on_dashboard': True,
        })
        _logger.info("Creado diario contable 'COBRO DE OTROS CONCEPTOS' (OTC)")

    return journal
```

### 2.2 Crear Método Principal: `_generate_utility_accounting_entries()`

**Ubicación:** Agregar después del método anterior

```python
def _generate_utility_accounting_entries(self):
    """
    Genera asiento contable automático para cobro de servicios públicos
    y otros conceptos asociados al contrato.

    Conceptos procesados:
    - Agua, Energía, Saneamiento (si servicios_publicos=True)
    - Internet (si internet=True)
    - TV Cable (si tv=True)
    - Administración Sostenimiento (si administracion_sostenimiento=True)
    - Costo Transacción (si costo_transaccion=True)

    Raises:
        UserError: Si faltan datos obligatorios o cuentas contables
    """
    self.ensure_one()

    # 1. Validaciones iniciales
    if not self.ecoerp_contract or self.state != 'sale':
        return

    if not self.partner_id:
        raise UserError(_("El contrato %s no tiene arrendatario definido.") % self.name)

    if not self.x_account_analytic_account_id:
        raise UserError(_("El contrato %s no tiene propiedad asociada.") % self.name)

    property_obj = self.x_account_analytic_account_id
    property_name = property_obj.name or 'Sin Nombre'
    company = self.company_id

    # 2. Obtener mes actual
    today = fields.Date.context_today(self)
    current_month = today.strftime("%Y-%m")
    current_year = today.year
    month_name_es = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    month_name = month_name_es.get(today.month, str(today.month))

    # 3. Validar duplicados
    ref_pattern = f"COBRO OTROS CONCEPTOS - Propiedad {property_name} - {month_name} {current_year}"
    existing_move = self.env['account.move'].search([
        ('ref', '=', ref_pattern),
        ('state', '!=', 'cancel')
    ], limit=1)

    if existing_move:
        _logger.info(
            "Asiento contable ya existe para contrato %s, propiedad %s, período %s-%s. Saltando...",
            self.name, property_name, month_name, current_year
        )
        return

    # 4. Obtener propietarios (NO beneficiarios)
    owner_lines = property_obj.owner_line_ids.filtered(lambda ol: not ol.is_main_payee)

    if not owner_lines:
        raise UserError(
            _("La propiedad '%s' no tiene propietarios definidos. "
              "Configure los propietarios antes de generar asientos.") % property_name
        )

    # Validar suma de participaciones = 100%
    total_participation = sum(owner_lines.mapped('participation_percent'))
    if not float_is_zero(total_participation - 100.0, precision_digits=2):
        raise UserError(
            _("La suma de participaciones de propietarios en '%s' es %.2f%%. "
              "Debe ser exactamente 100%%.") % (property_name, total_participation)
        )

    # 5. Obtener diario contable
    journal = self._get_or_create_utility_journal()

    # 6. Construir líneas del asiento
    line_vals = []

    # CONCEPTO 1-3: SERVICIOS PÚBLICOS (Agua, Energía, Saneamiento)
    if self.servicios_publicos:
        line_vals.extend(self._build_utility_lines_from_meters(
            current_month, owner_lines, company, property_obj
        ))

    # CONCEPTO 4: INTERNET
    if self.internet:
        if float_is_zero(self.monto_internet, precision_digits=2):
            raise UserError(
                _("El contrato %s tiene habilitado 'Internet' pero el monto es cero. "
                  "Configure el monto de internet.") % self.name
            )

        line_vals.extend(self._build_fixed_utility_lines(
            'internet',
            self.monto_internet,
            company.utility_internet_account_debit_id,
            company.utility_internet_account_credit_id,
            owner_lines,
            self.partner_id
        ))

    # CONCEPTO 5: TV CABLE
    if self.tv:
        if float_is_zero(self.monto_tv, precision_digits=2):
            raise UserError(
                _("El contrato %s tiene habilitado 'TV' pero el monto es cero. "
                  "Configure el monto de TV.") % self.name
            )

        line_vals.extend(self._build_fixed_utility_lines(
            'tv_cable',
            self.monto_tv,
            company.utility_tv_cable_account_debit_id,
            company.utility_tv_cable_account_credit_id,
            owner_lines,
            self.partner_id
        ))

    # CONCEPTO 6: ADMINISTRACIÓN SOSTENIMIENTO
    if self.administracion_sostenimiento:
        if float_is_zero(self.monto_administracion_sostenimiento, precision_digits=2):
            raise UserError(
                _("El contrato %s tiene habilitado 'Administración Sostenimiento' "
                  "pero el monto es cero. Configure el monto.") % self.name
            )

        line_vals.extend(self._build_fixed_utility_lines(
            'admin_sostenimiento',
            self.monto_administracion_sostenimiento,
            company.utility_admin_sostenimiento_account_debit_id,
            company.utility_admin_sostenimiento_account_credit_id,
            owner_lines,
            self.partner_id
        ))

    # CONCEPTO 7: COSTO TRANSACCIÓN (especial: mismo partner débito/crédito)
    if self.costo_transaccion:
        if float_is_zero(self.costo_transaccion_monto, precision_digits=2):
            raise UserError(
                _("El contrato %s tiene habilitado 'Costo Transacción' "
                  "pero el monto es cero. Configure el monto.") % self.name
            )

        line_vals.extend(self._build_transaction_cost_lines(
            self.costo_transaccion_monto,
            company.utility_transaction_cost_account_debit_id,
            company.utility_transaction_cost_account_credit_id,
            self.partner_id
        ))

    # 7. Validar que hay líneas para crear
    if not line_vals:
        _logger.info(
            "No hay conceptos habilitados para el contrato %s. No se genera asiento.",
            self.name
        )
        return

    # 8. Crear asiento contable
    move_vals = {
        'move_type': 'entry',
        'journal_id': journal.id,
        'date': today,
        'ref': ref_pattern,
        'line_ids': [(0, 0, line) for line in line_vals],
    }

    move = self.env['account.move'].create(move_vals)

    # 9. Publicar asiento
    move.action_post()

    _logger.info(
        "Asiento contable %s creado y publicado para contrato %s, propiedad %s, período %s-%s",
        move.name, self.name, property_name, month_name, current_year
    )

    return move
```

### 2.3 Método Helper: `_build_utility_lines_from_meters()`

**Ubicación:** Agregar después del método anterior

```python
def _build_utility_lines_from_meters(self, current_month, owner_lines, company, property_obj):
    """
    Construye líneas contables para servicios públicos basados en lecturas de medidor.

    Args:
        current_month (str): Período en formato YYYY-MM
        owner_lines (recordset): account.analytic.account.owner.line
        company (res.company): Compañía actual
        property_obj (account.analytic.account): Propiedad

    Returns:
        list: Lista de diccionarios con valores de líneas contables
    """
    line_vals = []

    # Mapeo de meter_type a configuración de cuentas
    meter_configs = {
        'water': {
            'name': 'Agua',
            'debit_account': company.utility_water_account_debit_id,
            'credit_account': company.utility_water_account_credit_id,
        },
        'energy': {
            'name': 'Energía',
            'debit_account': company.utility_energy_account_debit_id,
            'credit_account': company.utility_energy_account_credit_id,
        },
        'sanitation': {
            'name': 'Saneamiento',
            'debit_account': company.utility_sanitation_account_debit_id,
            'credit_account': company.utility_sanitation_account_credit_id,
        },
    }

    MeterReading = self.env['x.meter.reading']

    for meter_type, config in meter_configs.items():
        # Buscar lectura del mes actual
        reading = MeterReading.search([
            ('x_account_analytic_account_id', '=', property_obj.id),
            ('x_meter_id.meter_type', '=', meter_type),
            ('x_month', '=', current_month)
        ], limit=1)

        if not reading:
            raise UserError(
                _("No se encontró lectura de %s para la propiedad '%s' en el período %s. "
                  "Registre la lectura antes de generar asientos.")
                % (config['name'], property_obj.name, current_month)
            )

        # Validar existencia de cuentas
        if not config['debit_account']:
            raise UserError(
                _("No está configurada la cuenta débito para %s. "
                  "Configure en Ajustes → Industry Real Estate → Cuentas Contables.")
                % config['name']
            )

        if not config['credit_account']:
            raise UserError(
                _("No está configurada la cuenta crédito para %s. "
                  "Configure en Ajustes → Industry Real Estate → Cuentas Contables.")
                % config['name']
            )

        total_amount = reading.x_usage_cost

        if float_is_zero(total_amount, precision_digits=2):
            _logger.warning(
                "Lectura de %s para propiedad %s tiene costo cero. Saltando...",
                config['name'], property_obj.name
            )
            continue

        # LÍNEAS CRÉDITO: Por cada propietario (prorrateado)
        for owner_line in owner_lines:
            owner_amount = total_amount * (owner_line.participation_percent / 100.0)
            owner_amount = float_round(owner_amount, precision_digits=2)

            if float_is_zero(owner_amount, precision_digits=2):
                continue

            line_vals.append({
                'name': f"{config['name']} - {owner_line.owner_id.name} ({owner_line.participation_percent:.2f}%)",
                'account_id': config['credit_account'].id,
                'partner_id': owner_line.owner_id.id,
                'credit': owner_amount,
                'debit': 0.0,
            })

        # LÍNEA DÉBITO: Arrendatario (100%)
        line_vals.append({
            'name': f"{config['name']} - Arrendatario",
            'account_id': config['debit_account'].id,
            'partner_id': self.partner_id.id,
            'debit': total_amount,
            'credit': 0.0,
        })

    return line_vals
```

### 2.4 Método Helper: `_build_fixed_utility_lines()`

**Ubicación:** Agregar después del método anterior

```python
def _build_fixed_utility_lines(self, concept_name, amount, debit_account,
                                credit_account, owner_lines, tenant_partner):
    """
    Construye líneas contables para conceptos de monto fijo (internet, TV, etc.)
    con prorrateo entre propietarios.

    Args:
        concept_name (str): Nombre del concepto
        amount (float): Monto total
        debit_account (account.account): Cuenta débito
        credit_account (account.account): Cuenta crédito
        owner_lines (recordset): Propietarios
        tenant_partner (res.partner): Arrendatario

    Returns:
        list: Lista de diccionarios con valores de líneas contables
    """
    line_vals = []

    # Validar cuentas
    if not debit_account:
        raise UserError(
            _("No está configurada la cuenta débito para %s. "
              "Configure en Ajustes → Industry Real Estate → Cuentas Contables.")
            % concept_name.replace('_', ' ').title()
        )

    if not credit_account:
        raise UserError(
            _("No está configurada la cuenta crédito para %s. "
              "Configure en Ajustes → Industry Real Estate → Cuentas Contables.")
            % concept_name.replace('_', ' ').title()
        )

    # LÍNEAS CRÉDITO: Por cada propietario (prorrateado)
    for owner_line in owner_lines:
        owner_amount = amount * (owner_line.participation_percent / 100.0)
        owner_amount = float_round(owner_amount, precision_digits=2)

        if float_is_zero(owner_amount, precision_digits=2):
            continue

        line_vals.append({
            'name': f"{concept_name.replace('_', ' ').title()} - {owner_line.owner_id.name} ({owner_line.participation_percent:.2f}%)",
            'account_id': credit_account.id,
            'partner_id': owner_line.owner_id.id,
            'credit': owner_amount,
            'debit': 0.0,
        })

    # LÍNEA DÉBITO: Arrendatario (100%)
    line_vals.append({
        'name': f"{concept_name.replace('_', ' ').title()} - Arrendatario",
        'account_id': debit_account.id,
        'partner_id': tenant_partner.id,
        'debit': amount,
        'credit': 0.0,
    })

    return line_vals
```

### 2.5 Método Helper: `_build_transaction_cost_lines()`

**Ubicación:** Agregar después del método anterior

```python
def _build_transaction_cost_lines(self, amount, debit_account, credit_account, partner):
    """
    Construye líneas contables para costo de transacción.
    ESPECIAL: Mismo partner en débito y crédito (arrendatario).

    Args:
        amount (float): Monto del costo de transacción
        debit_account (account.account): Cuenta débito
        credit_account (account.account): Cuenta crédito
        partner (res.partner): Arrendatario (mismo para ambas líneas)

    Returns:
        list: Lista de diccionarios con valores de líneas contables
    """
    line_vals = []

    # Validar cuentas
    if not debit_account:
        raise UserError(
            _("No está configurada la cuenta débito para Costo Transacción. "
              "Configure en Ajustes → Industry Real Estate → Cuentas Contables.")
        )

    if not credit_account:
        raise UserError(
            _("No está configurada la cuenta crédito para Costo Transacción. "
              "Configure en Ajustes → Industry Real Estate → Cuentas Contables.")
        )

    # LÍNEA CRÉDITO: Arrendatario
    line_vals.append({
        'name': 'Costo Transacción - Arrendatario',
        'account_id': credit_account.id,
        'partner_id': partner.id,
        'credit': amount,
        'debit': 0.0,
    })

    # LÍNEA DÉBITO: Arrendatario (mismo partner)
    line_vals.append({
        'name': 'Costo Transacción - Arrendatario',
        'account_id': debit_account.id,
        'partner_id': partner.id,
        'debit': amount,
        'credit': 0.0,
    })

    return line_vals
```

**Resultado Esperado:**
- ✅ 1 método principal de generación de asientos
- ✅ 4 métodos helper especializados
- ✅ Validaciones completas de datos y cuentas
- ✅ Manejo de excepciones con mensajes claros
- ✅ Logging de operaciones

---

## FASE 3: Integración con Cron

### 3.1 Modificar `_cron_generate_mandates_and_invoices()`

**Archivo:** `c:\odoo-dev-bancasa\addons_realnet\industry_real_estate\models\sale_order.py`

**Ubicación:** Líneas ~1600-1640

**Modificación:**

```python
@api.model
def _cron_generate_mandates_and_invoices(self, limit=500):
    """
    Cron job para generar mandatos, facturas y asientos contables automáticos.

    Procesa contratos confirmados (state='sale') con ecoerp_contract=True.

    Args:
        limit (int): Número máximo de contratos a procesar por ejecución
    """
    contracts = self.search([
        ('ecoerp_contract', '=', True),
        ('state', '=', 'sale'),
    ], limit=limit)

    total = len(contracts)
    _logger.info("Procesando %d contratos para generación automática de documentos...", total)

    for idx, contract in enumerate(contracts, start=1):
        try:
            # Notificar progreso si disponible
            if hasattr(self.env, 'cr') and hasattr(self.env.cr, 'notify'):
                self.env.cr.notify(
                    'invoice_generation_progress',
                    {'current': idx, 'total': total}
                )

            # GENERACIÓN DE FACTURAS (EXISTENTE)
            contract._generate_all_documents_for_period()

            # GENERACIÓN DE ASIENTOS CONTABLES (NUEVO)
            contract._generate_utility_accounting_entries()

        except Exception as e:
            _logger.error(
                "Error procesando contrato %s: %s",
                contract.name,
                str(e),
                exc_info=True
            )
            # Continuar con el siguiente contrato
            continue

    _logger.info("Procesamiento completado: %d contratos procesados.", total)
```

**Resultado Esperado:**
- ✅ Integración transparente con cron existente
- ✅ Generación de asientos después de facturas
- ✅ Manejo de errores sin detener todo el proceso
- ✅ Logging detallado de operaciones

---

## FASE 4: Testing y Validación

### 4.1 Casos de Prueba

#### Test 1: Contrato con Servicios Públicos Completos
**Precondiciones:**
- Contrato con `servicios_publicos=True`
- Lecturas de agua, energía, saneamiento para mes actual
- 2 propietarios (60% / 40%)
- Cuentas configuradas en res.company

**Resultado Esperado:**
- Asiento con 9 líneas (3 servicios × 3 líneas cada uno)
- Suma débitos = suma créditos
- Referencia correcta

#### Test 2: Contrato con Conceptos Fijos
**Precondiciones:**
- `internet=True`, `tv=True`, `administracion_sostenimiento=True`
- Montos configurados: $50,000 / $30,000 / $100,000
- 3 propietarios (50% / 30% / 20%)

**Resultado Esperado:**
- Asiento con 12 líneas (3 conceptos × 4 líneas cada uno)
- Prorrateo correcto por propietario

#### Test 3: Costo Transacción Especial
**Precondiciones:**
- `costo_transaccion=True`
- `costo_transaccion_monto=15,000`
- Arrendatario: Juan Pérez

**Resultado Esperado:**
- Asiento con 2 líneas
- Ambas con partner_id = Juan Pérez
- Débito = Crédito = $15,000

#### Test 4: Validación de Duplicados
**Precondiciones:**
- Ejecutar cron dos veces en el mismo mes

**Resultado Esperado:**
- Primera ejecución: asientos creados
- Segunda ejecución: saltar contratos (log: "ya existe")

#### Test 5: Excepciones por Datos Faltantes
**Precondiciones:**
- `servicios_publicos=True`
- Sin lectura de energía para mes actual

**Resultado Esperado:**
- UserError: "No se encontró lectura de Energía..."
- No se crea asiento

#### Test 6: Excepciones por Cuentas Faltantes
**Precondiciones:**
- `internet=True`
- `utility_internet_account_debit_id` = False

**Resultado Esperado:**
- UserError: "No está configurada la cuenta débito para Internet..."

### 4.2 Validaciones de Integridad

```python
# Verificar que débitos = créditos
assert move.line_ids.mapped('debit').sum() == move.line_ids.mapped('credit').sum()

# Verificar número de líneas
expected_lines = (servicios_count * (propietarios_count + 1)) + \
                 (conceptos_fijos * (propietarios_count + 1)) + \
                 (2 if costo_transaccion else 0)
assert len(move.line_ids) == expected_lines

# Verificar estado publicado
assert move.state == 'posted'

# Verificar referencia única
assert not self.env['account.move'].search_count([
    ('ref', '=', move.ref),
    ('id', '!=', move.id)
]) > 0
```

---

## FASE 5: Documentación y Entrega

### 5.1 Actualizar `__manifest__.py`

**Agregar en descripción:**

```python
'description': """
    ...

    Nuevas Funcionalidades (v1.2):
    - Generación automática de asientos contables para servicios públicos
    - Cobro automático de internet, TV, administración sostenimiento
    - Soporte para costo de transacción
    - Prorrateo automático entre propietarios según participación
    - Validación de duplicados por período
""",
```

### 5.2 Crear Documentación Técnica

**Archivo:** `c:\odoo-dev-bancasa\addons_realnet\industry_real_estate\README_ASIENTOS_SERVICIOS.md`

Contenido:
- Descripción funcional
- Configuración paso a paso
- Ejemplos de uso
- Troubleshooting
- FAQ

### 5.3 Changelog

**Archivo:** `c:\odoo-dev-bancasa\addons_realnet\industry_real_estate\CHANGELOG.md`

```markdown
## [1.2.0] - 2025-10-29

### Added
- Asientos contables automáticos para servicios públicos (agua, energía, saneamiento)
- Cobro de conceptos fijos (internet, TV, administración sostenimiento)
- Concepto costo de transacción con lógica especial
- Diario contable "COBRO DE OTROS CONCEPTOS" (OTC)
- Validación de duplicados por período
- 4 nuevos campos de cuentas contables en res.company

### Modified
- `_cron_generate_mandates_and_invoices`: integración con generación de asientos
- res.config.settings: exposición de nuevas cuentas contables

### Technical
- 5 nuevos métodos en sale.order:
  - `_get_or_create_utility_journal()`
  - `_generate_utility_accounting_entries()`
  - `_build_utility_lines_from_meters()`
  - `_build_fixed_utility_lines()`
  - `_build_transaction_cost_lines()`
```

---

## Estructura de Archivos Modificados

```
industry_real_estate/
├── models/
│   ├── res_company.py                    [MODIFICAR - 4 campos nuevos]
│   ├── res_config_settings.py            [MODIFICAR - 4 campos related]
│   └── sale_order.py                     [MODIFICAR - 5 métodos + integración cron]
├── views/
│   └── res_config_settings_views.xml     [MODIFICAR - agregar campos UI]
├── PLAN_ASIENTOS_SERVICIOS_PUBLICOS.md   [NUEVO - este archivo]
├── README_ASIENTOS_SERVICIOS.md          [NUEVO - documentación]
└── CHANGELOG.md                          [MODIFICAR - agregar v1.2.0]
```

---

## Consideraciones Técnicas

### Precisión de Cálculos
- Usar `float_round(..., precision_digits=2)` para montos
- Validar suma propietarios = 100% con `float_is_zero`
- Redondeo en prorrateado: puede haber diferencias de centavos

### Performance
- Búsqueda de lecturas: índice en `x_month` (ya existe)
- Búsqueda de duplicados: índice en `ref` de account.move
- Limitar cron a 500 contratos por ejecución (configurable)

### Seguridad
- Validar permisos en `account.move.create()`
- No permitir creación manual de asientos con ref duplicada
- Logging de todas las operaciones críticas

### Multicompañía
- Cuentas filtradas por company_id
- Diario OTC global (no por compañía según PREGUNTA 22)
- Validar company_id en lecturas de medidor

---

## Cronograma Estimado

| Fase | Duración | Dependencias |
|------|----------|--------------|
| FASE 1: Configuración | 2 horas | Ninguna |
| FASE 2: Lógica | 6 horas | FASE 1 |
| FASE 3: Integración | 1 hora | FASE 2 |
| FASE 4: Testing | 4 horas | FASE 3 |
| FASE 5: Documentación | 2 horas | FASE 4 |
| **TOTAL** | **15 horas** | |

---

## Riesgos y Mitigación

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Lecturas de medidor faltantes | Alta | Alto | Excepción clara, guía al usuario |
| Cuentas no configuradas | Media | Alto | Validación previa, excepción descriptiva |
| Duplicados por ejecuciones múltiples | Media | Medio | Validación de referencia única |
| Errores de redondeo en prorrateo | Baja | Bajo | Usar float_round, documentar comportamiento |
| Sobrecarga en cron masivo | Baja | Medio | Limit=500, procesamiento por lotes |

---

## Entregables

1. ✅ Código Python modificado (3 archivos)
2. ✅ Vista XML actualizada (1 archivo)
3. ✅ Plan de implementación (este documento)
4. ✅ Documentación técnica
5. ✅ Casos de prueba documentados
6. ✅ Changelog actualizado

---

## Notas Adicionales

### Soporte a Beneficiarios
- **NO** se incluyen beneficiarios en asientos de servicios (PREGUNTA 14)
- Solo propietarios directos (`is_main_payee=False`)
- Si se requiere en el futuro, modificar lógica de `owner_lines`

### Campo `x_invoice_id` en `x.meter.reading`
- **NO** se usa actualmente (PREGUNTA 15)
- Es Many2one (solo 1 documento)
- Si se requiere vinculación, considerar crear Many2many

### Extensibilidad
- Arquitectura permite agregar nuevos conceptos fácilmente
- Separación clara entre:
  - Conceptos con medidor (método `_build_utility_lines_from_meters`)
  - Conceptos de monto fijo (método `_build_fixed_utility_lines`)
  - Conceptos especiales (método `_build_transaction_cost_lines`)

---

## Contacto y Soporte

- **Desarrollador:** Senior Odoo Developer
- **Fecha Plan:** 2025-10-29
- **Versión Plan:** 1.0
- **Estado:** ✅ Aprobado para Implementación

---

**FIN DEL PLAN**
