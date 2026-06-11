{
    "name": "Mega CRM Lost Reason on Fold Stage",
    "version": "18.0.1.0.0",
    "category": "MegaTecnicentro/CRM",
    "summary": "Require lost reason and closing note before moving opportunities to folded lost stages",
    "author": "Jorge Alberto Quiroz Sierra",
    "depends": ["crm"],
    "data": [
        "security/ir.model.access.csv",
        "views/crm_lost_stage_reason_wizard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mega_crm_lost_reason_on_fold_stage/static/src/js/crm_lost_stage_patch.js",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
} # type: ignore
