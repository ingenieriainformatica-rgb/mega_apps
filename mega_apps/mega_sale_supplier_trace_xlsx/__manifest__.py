{
    "name": "Trazabilidad de Proveedor por Venta (XLSX)",
    "version": "18.0.1.0.0",
    "category": "MegaTecnicentro/ConceptAccounting",
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://megatecnicentro.com/",
    "summary": (
        "Asistente de consulta y exportacion XLSX de trazabilidad de proveedor "
        "por venta (exacta / probable / no determinada), sin modificar facturas, "
        "inventario ni el reporte estandar de facturacion."
    ),
    "depends": [
        "account",
        "sale_stock",
        "purchase_stock",
        "stock_account",
    ],
    "data": [
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        "wizard/sale_supplier_trace_wizard_views.xml",
        "views/menu.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}  # type: ignore
