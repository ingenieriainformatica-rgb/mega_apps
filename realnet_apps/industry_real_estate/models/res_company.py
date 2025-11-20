from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    # --- Gestión de mora y cobranza ---
    percentage_of_arrears = fields.Float(
        string="Porcentaje de mora (%)",
        default=2.50,
        help="Porcentaje aplicado a facturas o rentas vencidas."
    )
    whatsapp_send_time = fields.Integer(
        string="Tiempo de envío WhatsApp (min)",
        default=2,
        help="Tiempo en minutos antes de enviar notificación por WhatsApp."
    )
    email_send_time = fields.Integer(
        string="Tiempo de envío Correo (min)",
        default=2,
        help="Tiempo en minutos antes de enviar notificación por correo electrónico."
    )

    # --- Notificaciones y responsables ---
    notify_late_changes_to_id = fields.Many2one(
        'res.users',
        string="Notificar cambios fuera de tiempo a",
        default=lambda self: self.env.user,
        help="Usuario que recibirá notificaciones de cambios fuera del tiempo permitido."
    )
    notify_to_legal_department = fields.Many2one(
        'res.users',
        string="Responsable área jurídica",
        help="Usuario o responsable del área jurídica para escalamientos."
    )
    time_to_notify_legal_department = fields.Integer(
        string="Tiempo para notificar al departamento jurídico (min)",
        default=2,
        help="Tiempo en minutos antes de escalar el caso al área jurídica."
    )
    notify_to_credit_bureau = fields.Many2one(
        'res.users',
        string="Responsable central de riesgo",
        help="Usuario responsable de notificar a la central de riesgo."
    )
    time_to_notify_to_credit_bureau = fields.Integer(
        string="Tiempo para notificar a central de riesgo (min)",
        default=2,
        help="Tiempo en minutos antes de enviar notificación a central de riesgo."
    )

    # --- Tickets automáticos ---
    ticket_per_user_type = fields.Boolean(
        string="Ticket por tipo de usuario",
        help="Generar tickets de seguimiento según tipo de usuario."
    )
    ticket_per_contract = fields.Boolean(
        string="Generar tickets por contrato",
        help="Crear automáticamente un ticket para cada contrato activo."
    )
    ticket_per_owners = fields.Boolean(
        string="Generar tickets por propietario",
        help="Generar tickets automáticos para los propietarios relacionados."
    )

    # --- Notificaciones de entrega/recepción ---
    notify_tenant_on_reception = fields.Boolean(
        string="Notificar recepción al arrendatario",
        help="Enviar notificación automática al arrendatario al registrar la recepción."
    )
    notify_tenant_on_delivery = fields.Boolean(
        string="Notificar entrega al arrendatario",
        help="Enviar notificación automática al arrendatario al registrar la entrega."
    )
    notify_owners_on_reception = fields.Boolean(
        string="Notificar recepción a propietarios",
        help="Enviar notificación automática al propietario al registrar la recepción."
    )
    notify_owners_on_delivery = fields.Boolean(
        string="Notificar entrega a propietarios",
        help="Enviar notificación automática al propietario al registrar la entrega."
    )

    # --- Responsables de tareas ---
    reception_owner_task = fields.Many2one(
        'res.users',
        string="Tarea: recepción (responsable)",
        help="Usuario responsable de gestionar las tareas de recepción de propiedades."
    )
    delivery_owner_task = fields.Many2one(
        'res.users',
        string="Tarea: entrega (responsable)",
        help="Usuario responsable de gestionar las tareas de entrega de propiedades."
    )

    # --- Plantillas de documentos (Firma) ---
    sign_template_contract_id = fields.Many2one(
        'sign.template',
        string='Plantilla: Contrato de Arrendamiento',
        help="Plantilla utilizada para generar contratos de arrendamiento."
    )
    sign_template_delivery_id = fields.Many2one(
        'sign.template',
        string='Plantilla: Acta de Entrega',
        help="Plantilla utilizada para generar el acta de entrega."
    )
    sign_template_reception_id = fields.Many2one(
        'sign.template',
        string='Plantilla: Acta de Recepción',
        help="Plantilla utilizada para generar el acta de recepción."
    )
    sign_template_clearance_delivery_id = fields.Many2one(
        'sign.template',
        string='Plantilla: Paz y Salvo (Entrega)',
        help="Plantilla utilizada para generar el paz y salvo de entrega."
    )
    sign_template_clearance_reception_id = fields.Many2one(
        'sign.template',
        string='Plantilla: Paz y Salvo (Recepción)',
        help="Plantilla utilizada para generar el paz y salvo de recepción."
    )
    sign_template_finish_id = fields.Many2one(
        'sign.template',
        string='Plantilla: Acta de Finalización',
        help="Plantilla utilizada para finalizar contratos de arrendamiento."
    )

    # --- porcentajes ---
    porcentaje_comision_inmobiliaria = fields.Float(
        string="Porcentaje comisión inmobiliaria (%)",
        default=10.0,
        help="Porcentaje de la administración inmobiliaria."
    )
    porcentaje_ipc = fields.Float(
        string="Porcentaje IPC (%)",
        default=0.0,
        help="Porcentaje de ajuste por IPC aplicado al canon de arrendamiento."
    )
    porcentaje_adicional_ipc = fields.Float(
        string="Porcentaje adicional al IPC (%)",
        default=0.0,        
        help="Porcentaje de ajuste adicional al IPC."
    )
    porcentaje_cobros_adicionales = fields.Float(
        string="Porcentaje de cobros adicionales (%)",
        default=0.0,        
        help="Porcentaje de ajuste para cobros adicionales."
    )
    monto_cobros_adicionales = fields.Integer(
        string="Cobros adicionales (monto fijo)",
        default=0,        
        help="cobros adicionales."
    )
    monto_adicional_paleria = fields.Integer(
        string="Monto adicional palería",
        default=0,        
        help="Monto adicional a papelería."
    )
    porcentaje_comision_inicial = fields.Float(
        string="Porcentaje comisión inicial (%)",
        default=0.0,        
        help="Porcentaje de comisión inicial aplicable solo al arrendatario."
    )
    tasa_usura = fields.Float(
        string="Tasa de usura (%)",
        default=0.0,
        help="Tasa máxima permitida para cálculo de intereses o IPC."
    )
    dias_gracia_mora = fields.Integer(
        string="Días de gracia para mora",
        default=3,
        help="Número de días de gracia antes de aplicar mora."
    )
    
    porcentaje_comision_inmobiliaria = fields.Float(
        string="Comisión inmobiliaria (%)",
    )
    ecoerp_product_canon_id = fields.Many2one(
        'product.product', string="Producto Canon"
    )
    ecoerp_product_owner_payment_id = fields.Many2one(
        'product.product', string="Producto Pago a Propietario"
    )

    # --- Servicios Públicos (precios por unidad) ---
    utility_price_energy = fields.Float(
        string="Precio Energía",
        default=0.0,
        help="Precio por unidad para el servicio de energía (luz)."
    )
    utility_price_water = fields.Float(
        string="Precio Agua",
        default=0.0,
        help="Precio por unidad para el servicio de agua."
    )
    utility_price_sanitation = fields.Float(
        string="Precio Saneamiento",
        default=0.0,
        help="Precio por unidad para el servicio de saneamiento (aseo/alcantarillado)."
    )
    utility_price_misc = fields.Float(
        string="Precio Varios",
        default=0.0,
        help="Precio por unidad para otros conceptos de servicios públicos."
    )
    
    # ========== SERVICIOS PÚBLICOS ==========
    # AGUA
    utility_water_account_debit_id = fields.Many2one(
        'account.account',
        string="Cuenta Débito - Agua",
        domain="[('deprecated', '=', False), ('company_id', '=', id)]",
        help="Cuenta débito para servicios de agua (ej: 28150512)"
    )
    
    utility_water_account_credit_id = fields.Many2one(
        'account.account',
        string="Cuenta Crédito - Agua",
        domain="[('deprecated', '=', False), ('company_id', '=', id)]",
        help="Cuenta crédito para CxC agua al arrendatario (ej: 13802010)"
    )
    
    # ENERGÍA
    utility_energy_account_debit_id = fields.Many2one(
        'account.account',
        string="Cuenta Débito - Energía",
        domain="[('deprecated', '=', False), ('company_id', '=', id)]",
        help="Cuenta débito para servicios de energía (ej: 28150512)"
    )
    
    utility_energy_account_credit_id = fields.Many2one(
        'account.account',
        string="Cuenta Crédito - Energía",
        domain="[('deprecated', '=', False), ('company_id', '=', id)]",
        help="Cuenta crédito para CxC energía"
    )
    
    # SANEAMIENTO
    utility_sanitation_account_debit_id = fields.Many2one(
        'account.account',
        string="Cuenta Débito - Saneamiento",
        domain="[('deprecated', '=', False), ('company_id', '=', id)]"
    )
    
    utility_sanitation_account_credit_id = fields.Many2one(
        'account.account',
        string="Cuenta Crédito - Saneamiento",
        domain="[('deprecated', '=', False), ('company_id', '=', id)]"
    )
    
    # INTERNET
    utility_internet_account_debit_id = fields.Many2one(
        'account.account',
        string="Cuenta Débito - Internet",
        domain="[('deprecated', '=', False), ('company_id', '=', id)]"
    )
    
    utility_internet_account_credit_id = fields.Many2one(
        'account.account',
        string="Cuenta Crédito - Internet",
        domain="[('deprecated', '=', False), ('company_id', '=', id)]"
    )
    
    # TV CABLE
    utility_tv_cable_account_debit_id = fields.Many2one(
        'account.account',
        string="Cuenta Débito - TV Cable",
        domain="[('deprecated', '=', False), ('company_id', '=', id)]"
    )
    
    utility_tv_cable_account_credit_id = fields.Many2one(
        'account.account',
        string="Cuenta Crédito - TV Cable",
        domain="[('deprecated', '=', False), ('company_id', '=', id)]"
    )
    
    # REPARACIONES
    utility_repairs_account_debit_id = fields.Many2one(
        'account.account',
        string="Cuenta Débito - Reparaciones",
        domain="[('deprecated', '=', False), ('company_id', '=', id)]"
    )
    
    utility_repairs_account_credit_id = fields.Many2one(
        'account.account',
        string="Cuenta Crédito - Reparaciones",
        domain="[('deprecated', '=', False), ('company_id', '=', id)]"
    )
    
    # OTROS/VARIOS
    utility_misc_account_debit_id = fields.Many2one(
        'account.account',
        string="Cuenta Débito - Varios",
        domain="[('deprecated', '=', False), ('company_id', '=', id)]"
    )
    
    utility_misc_account_credit_id = fields.Many2one(
        'account.account',
        string="Cuenta Crédito - Varios",
        domain="[('deprecated', '=', False), ('company_id', '=', id)]"
    )

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

