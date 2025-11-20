# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # --- Gestión de mora y tiempos de notificación (related a company_id) ---
    """ percentage_of_arrears = fields.Float(
        string="Porcentaje de mora",
        related='company_id.percentage_of_arrears',
        readonly=False,
        help="Porcentaje de mora a aplicar a saldos vencidos."
    ) """
    whatsapp_send_time = fields.Integer(
        string="Tiempo de envío WhatsApp (min)",
        related='company_id.whatsapp_send_time',
        readonly=False
    )
    email_send_time = fields.Integer(
        string="Tiempo de envío correo (min)",
        related='company_id.email_send_time',
        readonly=False
    )

    notify_late_changes_to_id = fields.Many2one(
        'res.users',
        string="Notificar cambios fuera de tiempo a",
        related='company_id.notify_late_changes_to_id',
        readonly=False
    )
    notify_to_legal_department = fields.Many2one(
        'res.users',
        string="Responsable área jurídica",
        related='company_id.notify_to_legal_department',
        readonly=False
    )
    time_to_notify_legal_department = fields.Integer(
        string="Escalar a jurídica tras (min)",
        related='company_id.time_to_notify_legal_department',
        readonly=False
    )
    notify_to_credit_bureau = fields.Many2one(
        'res.users',
        string="Responsable central de riesgo",
        related='company_id.notify_to_credit_bureau',
        readonly=False
    )
    time_to_notify_to_credit_bureau = fields.Integer(
        string="Notificar central de riesgo tras (min)",
        related='company_id.time_to_notify_to_credit_bureau',
        readonly=False
    )

    # --- Tickets ---
    ticket_per_user_type = fields.Boolean(
        string="Ticket por tipo de usuario",
        related='company_id.ticket_per_user_type',
        readonly=False
    )
    ticket_per_contract = fields.Boolean(
        string="Generar tickets por contrato",
        related='company_id.ticket_per_contract',
        readonly=False
    )
    ticket_per_owners = fields.Boolean(
        string="Generar tickets por propietario",
        related='company_id.ticket_per_owners',
        readonly=False
    )

    # --- Notificaciones de recepción/entrega ---
    notify_tenant_on_reception = fields.Boolean(
        string="Notificar recepción al arrendatario",
        related='company_id.notify_tenant_on_reception',
        readonly=False
    )
    notify_tenant_on_delivery = fields.Boolean(
        string="Notificar entrega al arrendatario",
        related='company_id.notify_tenant_on_delivery',
        readonly=False
    )
    notify_owners_on_reception = fields.Boolean(
        string="Notificar recepción a propietarios",
        related='company_id.notify_owners_on_reception',
        readonly=False
    )
    notify_owners_on_delivery = fields.Boolean(
        string="Notificar entrega a propietarios",
        related='company_id.notify_owners_on_delivery',
        readonly=False
    )

    # --- Responsables de tareas ---
    reception_owner_task = fields.Many2one(
        'res.users',
        string="Recepción (responsable)",
        related='company_id.reception_owner_task',
        readonly=False
    )
    delivery_owner_task = fields.Many2one(
        'res.users',
        string="Entrega (responsable)",
        related='company_id.delivery_owner_task',
        readonly=False
    )

    # --- Plantillas de firma (Sign) ---
    sign_template_contract_id = fields.Many2one(
        related='company_id.sign_template_contract_id',
        readonly=False
    )
    sign_template_delivery_id = fields.Many2one(
        related='company_id.sign_template_delivery_id',
        readonly=False
    )
    sign_template_reception_id = fields.Many2one(
        related='company_id.sign_template_reception_id',
        readonly=False
    )
    sign_template_clearance_delivery_id = fields.Many2one(
        related='company_id.sign_template_clearance_delivery_id',
        readonly=False
    )
    sign_template_clearance_reception_id = fields.Many2one(
        related='company_id.sign_template_clearance_reception_id',
        readonly=False
    )
    sign_template_finish_id = fields.Many2one(
        related='company_id.sign_template_finish_id',
        readonly=False
    )
    porcentaje_ipc = fields.Float(
        related='company_id.porcentaje_ipc',
        readonly=False
    )
    # --- Parámetros ECOERP (persisten en ir.config_parameter) ---
    ecoerp_default_admin_percent = fields.Float(
       related='company_id.porcentaje_comision_inmobiliaria',
        readonly=False
    )
    ecoerp_product_canon_id = fields.Many2one(
        'product.product',
        related='company_id.ecoerp_product_canon_id',
        readonly=False
    )
    ecoerp_product_owner_payment_id = fields.Many2one(
        'product.product',
        related='company_id.ecoerp_product_owner_payment_id',
        readonly=False
    )

    # --- IPC / Usura (related a company_id) ---
    
    tasa_usura = fields.Float(
        string="Tasa de usura (%)",
        related='company_id.tasa_usura',
        readonly=False
    )

    # Alias para coherencia con otros puntos del sistema (opcional)
    porcentaje_mora = fields.Float(
        string="Porcentaje de mora (%)",
        related='company_id.percentage_of_arrears',
        readonly=False
    )
    
    dias_gracia_mora = fields.Integer(
        string="Días de gracia para mora",
        related='company_id.dias_gracia_mora',
        readonly=False
    )

    # --- Precios de Servicios Públicos ---
    utility_price_energy = fields.Float(
        string="Precio Energía",
        related='company_id.utility_price_energy',
        readonly=False,
        help="Precio por unidad para el servicio de energía"
    )

    utility_price_water = fields.Float(
        string="Precio Agua",
        related='company_id.utility_price_water',
        readonly=False,
        help="Precio por unidad para el servicio de agua"
    )

    utility_price_sanitation = fields.Float(
        string="Precio Saneamiento",
        related='company_id.utility_price_sanitation',
        readonly=False,
        help="Precio por unidad para saneamiento"
    )

    utility_price_misc = fields.Float(
        string="Precio Varios",
        related='company_id.utility_price_misc',
        readonly=False,
        help="Precio por unidad para otros conceptos"
    )

    # --- Configuración de la asociación de las cuentas contables de los otros conceptos a cobrar ---
    # AGUA
    utility_water_account_debit_id = fields.Many2one(
        'account.account',
        string="Cuenta Débito - Agua",
        related='company_id.utility_water_account_debit_id',
        readonly=False,
    )
    
    utility_water_account_credit_id = fields.Many2one(
        'account.account',
        string="Cuenta Crédito - Agua",
        related='company_id.utility_water_account_credit_id',
        readonly=False,
    )
    
    # ENERGÍA
    utility_energy_account_debit_id = fields.Many2one(
        'account.account',
        related='company_id.utility_energy_account_debit_id',
        readonly=False
    )
    
    utility_energy_account_credit_id = fields.Many2one(
        'account.account',
        related='company_id.utility_energy_account_credit_id',
        readonly=False
    )
    
    # SANEAMIENTO
    utility_sanitation_account_debit_id = fields.Many2one(
        'account.account',
        related='company_id.utility_sanitation_account_debit_id',
        readonly=False
    )
    
    utility_sanitation_account_credit_id = fields.Many2one(
        'account.account',
        related='company_id.utility_sanitation_account_credit_id',
        readonly=False
    )
    
    # INTERNET
    utility_internet_account_debit_id = fields.Many2one(
        'account.account',
        related='company_id.utility_internet_account_debit_id',
        readonly=False
    )
    
    utility_internet_account_credit_id = fields.Many2one(
        'account.account',
        related='company_id.utility_internet_account_credit_id',
        readonly=False
    )
    
    # TV CABLE
    utility_tv_cable_account_debit_id = fields.Many2one(
        'account.account',
        related='company_id.utility_tv_cable_account_debit_id',
        readonly=False
    )
    
    utility_tv_cable_account_credit_id = fields.Many2one(
        'account.account',
        related='company_id.utility_tv_cable_account_credit_id',
        readonly=False
    )
    
    # REPARACIONES
    utility_repairs_account_debit_id = fields.Many2one(
        'account.account',
        related='company_id.utility_repairs_account_debit_id',
        readonly=False
    )
    
    utility_repairs_account_credit_id = fields.Many2one(
        'account.account',
        related='company_id.utility_repairs_account_credit_id',
        readonly=False
    )
    
    # VARIOS
    utility_misc_account_debit_id = fields.Many2one(
        'account.account',
        related='company_id.utility_misc_account_debit_id',
        readonly=False
    )
    
    utility_misc_account_credit_id = fields.Many2one(
        'account.account',
        related='company_id.utility_misc_account_credit_id',
        readonly=False
    )

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


    # --- Acción auxiliar (modal de ejemplo) ---
    def action_open_popup(self):
        return {
            'name': 'reception.template popup',
            'type': 'ir.actions.act_window',
            'res_model': 'reception.template',
            'view_mode': 'form',
            'view_id': self.env.ref('bambu.reception_view_form').id,
            'target': 'new',
            'context': {
                'default_field1': 'valor por defecto',
            }
        }
        
    def write(self, vals):
        """ res = super(ResConfigSettings, self).write()
        for record in self:
            if record.porcentaje_ipc > record.taza_usura:
                raise ValueError(_("El porcentaje IPC no puede ser mayor que la taza de usura."))
        # Aquí puedes agregar lógica adicional si es necesario
        return res """

    # --- Validaciones ---
    @api.constrains('porcentaje_ipc', 'tasa_usura')
    def _check_ipc_vs_usura(self):
        for rec in self:
            if rec.porcentaje_ipc and rec.tasa_usura and rec.porcentaje_ipc > rec.tasa_usura:
                raise ValidationError(_("El porcentaje IPC no puede ser mayor que la tasa de usura."))

    def write(self, vals):
        """
        Validamos con los valores efectivos que se van a guardar (mezcla de 'vals' + valores actuales),
        para evitar que se llegue a escribir una combinación inválida.
        """
        for rec in self:
            new_ipc = vals.get('porcentaje_ipc', rec.porcentaje_ipc)
            new_usura = vals.get('tasa_usura', rec.tasa_usura)
            if new_ipc and new_usura and new_ipc > new_usura:
                raise ValidationError(_("El porcentaje IPC no puede ser mayor que la tasa de usura."))
        return super(ResConfigSettings, self).write(vals)
