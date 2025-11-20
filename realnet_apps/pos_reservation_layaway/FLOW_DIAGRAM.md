# Diagrama de Flujo - Facturación Electrónica de Apartados

## Flujo Principal: Facturación desde POS

```
┌─────────────────────────────────────────────────────────────────┐
│                    APARTADO COMPLETAMENTE PAGADO                 │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────────┐
         │  Usuario hace click en             │
         │  "Crear Factura" (botón verde)     │
         │  O                                  │
         │  Sistema pregunta después de abono │
         └────────────┬───────────────────────┘
                      │
                      ▼
         ┌────────────────────────────────────┐
         │  layaway_payment_popup.js          │
         │  createInvoice() ó                 │
         │  createInvoiceAfterPayment()       │
         └────────────┬───────────────────────┘
                      │
                      │ RPC Call
                      ▼
         ┌────────────────────────────────────┐
         │  Backend: pos_reservation.py       │
         │  create_invoice_from_pos_          │
         │  with_validation()                 │
         └────────────┬───────────────────────┘
                      │
                      ▼
         ┌────────────────────────────────────┐
         │  1. Validar: apartado pagado 100%  │
         └────────────┬───────────────────────┘
                      │
                      ▼
         ┌────────────────────────────────────┐
         │  2. Crear factura (account.move)   │
         │     - Líneas con precios congelados│
         │     - Impuestos del producto       │
         └────────────┬───────────────────────┘
                      │
                      ▼
         ┌────────────────────────────────────┐
         │  3. Validar factura                │
         │     invoice.action_post()          │
         └────────────┬───────────────────────┘
                      │
                      │ (Automático por l10n_co)
                      ▼
         ┌────────────────────────────────────┐
         │  4. Envío a DIAN                   │
         │     - Genera XML UBL 2.1           │
         │     - Firma digitalmente           │
         │     - Envía a webservice DIAN      │
         │     - Obtiene validación           │
         └────────────┬───────────────────────┘
                      │
                      ▼
         ┌────────────────────────────────────┐
         │  5. DIAN responde                  │
         │     - CUFE generado                │
         │     - QR Code URL                  │
         │     - Estado: invoice_accepted     │
         └────────────┬───────────────────────┘
                      │
                      ▼
         ┌────────────────────────────────────┐
         │  6. Preparar datos para recibo     │
         │     _prepare_invoice_data_for_pos()│
         │     - Extraer CUFE                 │
         │     - Extraer QR del XML           │
         │     - Formatear líneas             │
         └────────────┬───────────────────────┘
                      │
                      ▼
         ┌────────────────────────────────────┐
         │  7. Liberar reservas inventario    │
         │     resv.hold_ids.action_release() │
         └────────────┬───────────────────────┘
                      │
                      ▼
         ┌────────────────────────────────────┐
         │  8. Crear picking de entrega       │
         │     _create_final_delivery_picking()│
         └────────────┬───────────────────────┘
                      │
                      ▼
         ┌────────────────────────────────────┐
         │  9. Conciliar pagos previos        │
         │     _reconcile_reservation_credits()│
         └────────────┬───────────────────────┘
                      │
                      ▼
         ┌────────────────────────────────────┐
         │  10. Retornar resultado a frontend │
         │      {                             │
         │        success: true,              │
         │        invoice_data: {...},        │
         │        cufe: "...",                │
         │        qr_code_url: "...",         │
         │      }                             │
         └────────────┬───────────────────────┘
                      │
                      ▼
         ┌────────────────────────────────────┐
         │  Frontend recibe resultado         │
         │  layaway_payment_popup.js          │
         └────────────┬───────────────────────┘
                      │
                      ▼
         ┌────────────────────────────────────┐
         │  11. Mostrar notificación          │
         │      "Factura validada por DIAN"   │
         │      + número + CUFE               │
         └────────────┬───────────────────────┘
                      │
                      ▼
         ┌────────────────────────────────────┐
         │  12. Preparar datos para imprimir  │
         │      printInvoiceReceipt()         │
         │      - Header empresa              │
         │      - Datos cliente               │
         │      - Líneas productos            │
         │      - CUFE                        │
         │      - QR Code                     │
         └────────────┬───────────────────────┘
                      │
                      ▼
         ┌────────────────────────────────────┐
         │  13. Imprimir recibo               │
         │      this.printer.print(           │
         │        LayawayInvoiceReceipt,      │
         │        data,                       │
         │        {webPrintFallback: true}    │
         │      )                             │
         └────────────┬───────────────────────┘
                      │
                      ▼
         ┌────────────────────────────────────┐
         │  Integración sh_pos_all_in_one     │
         │  - Usa impresora configurada       │
         │  - Respeta formato (A3/A4/A5)      │
         │  - Compatible con térmicas         │
         └────────────┬───────────────────────┘
                      │
                      ▼
         ┌────────────────────────────────────┐
         │  ✅ RECIBO IMPRESO                 │
         │                                    │
         │  [Logo Empresa]                    │
         │  FACTURA ELECTRÓNICA               │
         │  No: INV-001                       │
         │                                    │
         │  Cliente: Juan Pérez               │
         │  NIT: 123456789                    │
         │                                    │
         │  Productos...                      │
         │  Total: $350,000                   │
         │                                    │
         │  CUFE:                             │
         │  a1b2c3d4e5f6...                   │
         │                                    │
         │  [QR CODE IMAGE]                   │
         │                                    │
         │  ✓ Factura Aceptada DIAN           │
         └────────────────────────────────────┘
```

## Integración con Módulos

```
┌──────────────────────────────────────────────────────────────────┐
│                         ODOO MODULES                             │
└──────────────────────────────────────────────────────────────────┘

┌───────────────────┐     ┌────────────────────┐     ┌─────────────┐
│                   │     │                    │     │             │
│  pos_reservation  │────▶│  sh_pos_all_in_one │────▶│  l10n_co    │
│  _layaway         │     │  _retail           │     │  _dian      │
│                   │     │                    │     │             │
│  - Apartados      │     │  - POS System      │     │  - DIAN API │
│  - Abonos         │     │  - Impresión       │     │  - CUFE     │
│  - Facturación    │     │  - Recibos         │     │  - QR       │
│                   │     │  - Configuración   │     │  - XML UBL  │
└───────┬───────────┘     └─────────┬──────────┘     └──────┬──────┘
        │                           │                       │
        │                           │                       │
        └───────────────┬───────────┴───────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │                       │
            │  realnet_anticipos    │
            │                       │
            │  - Cuenta anticipos   │
            │  - Conciliación       │
            │                       │
            └───────────────────────┘
```

## Flujo de Datos: CUFE y QR

```
DIAN Webservice
     │
     │ 1. Envía factura XML
     ▼
┌─────────────────┐
│  DIAN Valida    │
│  - Firma        │
│  - Estructura   │
│  - Rangos       │
└────────┬────────┘
         │
         │ 2. Genera CUFE
         │    (Código Único)
         ▼
┌──────────────────────────────────────┐
│  CUFE: a1b2c3d4e5f6...              │
│  (SHA-256 de datos factura)         │
└────────┬─────────────────────────────┘
         │
         │ 3. Retorna XML con:
         │    - CUFE en campo específico
         │    - QR Code URL
         ▼
┌──────────────────────────────────────┐
│  XML Response (UBL 2.1)             │
│                                     │
│  <DianExtensions>                   │
│    <QRCode>                         │
│      https://catalogo-vpfe.dian...  │
│    </QRCode>                        │
│  </DianExtensions>                  │
└────────┬─────────────────────────────┘
         │
         │ 4. Odoo almacena
         ▼
┌──────────────────────────────────────┐
│  account.move (Factura)             │
│                                     │
│  - l10n_co_edi_cufe_cude_ref        │
│  - l10n_co_dian_state               │
│  - l10n_co_dian_attachment_id (XML) │
└────────┬─────────────────────────────┘
         │
         │ 5. Módulo extrae
         ▼
┌──────────────────────────────────────┐
│  _prepare_invoice_data_for_pos()    │
│                                     │
│  - Lee CUFE del campo               │
│  - Parsea XML con lxml              │
│  - Busca QRCode en namespace        │
│  - Genera URL para código QR        │
└────────┬─────────────────────────────┘
         │
         │ 6. Frontend recibe
         ▼
┌──────────────────────────────────────┐
│  printInvoiceReceipt()              │
│                                     │
│  receiptData = {                    │
│    invoice_data: {                  │
│      cufe: "...",                   │
│      qr_code_url: "/report/         │
│        barcode/?type=QR&            │
│        value=https://..."           │
│    }                                │
│  }                                  │
└────────┬─────────────────────────────┘
         │
         │ 7. Template renderiza
         ▼
┌──────────────────────────────────────┐
│  invoice_receipt_templates.xml      │
│                                     │
│  <div t-if="data.invoice_data.cufe">│
│    CUFE: <t t-esc="...cufe"/>      │
│  </div>                             │
│                                     │
│  <img t-att-src="...qr_code_url"/> │
└────────┬─────────────────────────────┘
         │
         │ 8. Imprime
         ▼
    [RECIBO FÍSICO CON CUFE Y QR]
```

## Manejo de Errores

```
Crear Factura
     │
     ▼
¿Apartado pagado 100%?
     │
     ├─ No ──▶ ValidationError
     │         "Saldo pendiente: XX"
     │
     └─ Sí
        │
        ▼
   ¿Ya facturado?
        │
        ├─ Sí ──▶ UserError
        │         "Ya tiene factura"
        │
        └─ No
           │
           ▼
      Crear account.move
           │
           ├─ Error ──▶ Log + return {success: false}
           │
           └─ OK
              │
              ▼
         action_post()
              │
              ├─ Error DIAN ──▶ Factura queda en borrador
              │                 Usuario puede reintentar
              │
              └─ OK
                 │
                 ▼
            Refrescar datos
                 │
                 ▼
            ¿CUFE obtenido?
                 │
                 ├─ No ──▶ Advertencia en logs
                 │         Factura válida sin CUFE
                 │
                 └─ Sí
                    │
                    ▼
               ¿QR encontrado en XML?
                    │
                    ├─ No ──▶ Usa CUFE como fallback
                    │
                    └─ Sí
                       │
                       ▼
                  Imprime recibo
                       │
                       ├─ Error ──▶ Notificación warning
                       │            "Factura creada pero
                       │             error al imprimir"
                       │
                       └─ OK
                          │
                          ▼
                     ✅ ÉXITO
```
