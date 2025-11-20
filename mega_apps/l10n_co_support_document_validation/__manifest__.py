# -*- coding: utf-8 -*-
{
    'name': 'Colombia - Validación Secuencial de Documentos Soporte',
    'version': '1.0.4',
    'category': 'Accounting/Localizations',
    'summary': 'Valida que los documentos soporte se envíen a DIAN en orden secuencial',
    'description': """
Validación Secuencial de Documentos Soporte para Colombia
==========================================================

Este módulo valida que los documentos soporte (facturas de compra) se envíen
a la DIAN en orden secuencial antes de permitir confirmar nuevos documentos.

Características principales:
-----------------------------
* Detecta automáticamente documentos soporte
* Verifica que el documento anterior esté enviado a DIAN
* Dos modos de operación: Bloquear o Solo Advertir
* Permite bypass manual con permisos especiales
* Integración completa con l10n_co_dian

Requerimientos:
---------------
* Módulo l10n_co_dian instalado y configurado
* Journals de compra configurados como documentos soporte
* Resolución DIAN configurada en el journal

Normativa:
----------
* Cumple con requisitos de secuencialidad DIAN
* Previene problemas de auditoría
* Mejora control de documentos electrónicos
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'l10n_co',
        'l10n_co_dian',  # CRÍTICO: Requiere módulo DIAN
    ],
    'data': [
        # Seguridad - ORDEN IMPORTANTE
        'security/support_document_security.xml',
        'security/ir.model.access.csv',

        # Configuración
        'data/company_data.xml',

        # Vistas
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': None,
    'uninstall_hook': None,
}
