{
    "name": "Mega Caja Legalizacion",
    "version": "18.0.1.0.0",
    "category": "MegaTecnicentro/ControlCash",
    "summary": "Legalizacion de egresos dentro del control de efectivo",
    "author": "Isaac Vasquez",
    "license": "LGPL-3",
    "depends": ["base", "account", "account_petty_cash", "mega_petty_cash_current_balance"],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "data/cleanup_legacy_security.xml",
        "data/ir_cron.xml",
        "views/caja_legalizacion_seguimiento_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mega_caja_legalizacion/static/src/xml/legalized_control_panel_notice.xml",
        ],
    },
    "installable": True,
    "application": False,
}  #type: ignore
