{
    "name": "Mega Aged Receivable - Customer Column in XLSX",
    "version": "18.0.1.0.0",
    "summary": "Agrega la columna Cliente, repetida en cada fila de detalle, a la exportación XLSX del informe Cuentas por Cobrar Vencidas (Aged Receivable).",
    "category": "MegaTecnicentro/Accounting",
    "sequence": -350,
    "website": "https://megatecnicentro.com/",
    "author": "Jorge Alberto Quiroz Sierra",
    "depends": ["account", "account_reports"],
    "data": [
        "data/aged_receivable_customer_column.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}  # type: ignore
