{
    "name": "Realnet - Consecutivos Globales CE/CI Pagos Clientes y Proveedores",
    "version": "1.0",
    "summary": "Asigna un único número global CE/CI según Payment Type al validar pagos (outbound=CE / inbound=CI).",
    "author": "Realnet",
    "depends": ["account", "custom_accounting_reports", "l10n_co_edi"],
    "data": [
        "data/ir_sequence.xml",
        "views/account_payment_views.xml",
        "views/account_move_views.xml",
        "views/report_payment_receipt_templates.xml",
        "views/report_journal_entry_templates.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": True,
    "post_init_hook": "post_init_sync_ceci_sequences",
}
