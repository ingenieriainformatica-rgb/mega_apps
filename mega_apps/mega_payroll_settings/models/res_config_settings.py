import logging
from odoo import fields, models, api  #type:ignore

_logger = logging.getLogger(__name__)



class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_l10n_co_hr_payroll = fields.Boolean(string='Colombian Payroll')

    smmlv_value = fields.Monetary(related="company_id.smmlv_value", string="SMMLV", readonly=False,
                                  currency_field='currency_id')
    uvt_value = fields.Monetary(related="company_id.uvt_value", string="UVT", readonly=False,
                                currency_field='currency_id')
    stm_value = fields.Monetary(related="company_id.stm_value",
                                string="Monthly transportation allowance", readonly=False,
                                currency_field='currency_id')
    
    # 👇 porcentajes de salud y pensión trabajador
    salud_employee_rate = fields.Float(
        related="company_id.salud_employee_rate",
        string="Salud trabajador (%)",
        readonly=False
    )
    pension_employee_rate = fields.Float(
        related="company_id.pension_employee_rate",
        string="Pensión trabajador (%)",
        readonly=False
    )

    # Employer contribution rates (🔥 nuevos campos)
    salud_employer_rate = fields.Float(
        string="Salud empleador (%)",
        related="company_id.salud_employer_rate",
        readonly=False
    )
    pension_employer_rate = fields.Float(
        string="Pensión empleador (%)",
        related="company_id.pension_employer_rate",
        readonly=False
    )

    # times
    daily_overtime = fields.Float(
        related="company_id.daily_overtime",
        string="% Daily",
        readonly=False
    )
    overtime_night_hours = fields.Float(
        related="company_id.overtime_night_hours",
        string="% Night hours",
        readonly=False
    )
    hours_night_surcharge = fields.Float(
        related="company_id.hours_night_surcharge",
        string="% Night hours",
        readonly=False
    )
    sunday_holiday_daily_overtime = fields.Float(
        related="company_id.sunday_holiday_daily_overtime",
        string="% Sunday and Holiday daily",
        readonly=False
    )
    daily_surcharge_hours_sundays_holidays = fields.Float(
        related="company_id.daily_surcharge_hours_sundays_holidays",
        string="% Daily hours on sundays and holidays",
        readonly=False
    )
    sunday_night_overtime_holidays = fields.Float(
        related="company_id.sunday_night_overtime_holidays",
        string="% Sunday night and holidays",
        readonly=False
    )
    sunday_holidays_night_surcharge_hours = fields.Float(
        related="company_id.sunday_holidays_night_surcharge_hours",
        string="% Sunday and holidays night hours",
        readonly=False
    )

    # Test
    edi_payroll_is_not_test = fields.Boolean(related="company_id.edi_payroll_is_not_test",
                                             string="Production environment", default=False, readonly=False)

    # Enable/disable electronic payroll for company
    edi_payroll_enable = fields.Boolean(related="company_id.edi_payroll_enable",
                                        string="Enable electronic payroll for this company", default=False,
                                        readonly=False)

    # Test
    edi_payroll_test_set_id = fields.Char(related="company_id.edi_payroll_test_set_id", string="TestSetId",
                                          readonly=False)

    # Software ID and pin
    edi_payroll_id = fields.Char(related="company_id.edi_payroll_id", string="Software ID", readonly=False)
    edi_payroll_pin = fields.Char(related="company_id.edi_payroll_pin", string="Software PIN", readonly=False)

    # Consolidated payroll
    edi_payroll_consolidated_enable = fields.Boolean(related="company_id.edi_payroll_consolidated_enable",
                                                     string="Enable consolidated electronic payroll for this company",
                                                     default=False, readonly=False)

    # DIAN validation
    edi_payroll_always_validate = fields.Boolean(related="company_id.edi_payroll_always_validate",
                                                 string="Always validate payslips",
                                                 default=False, readonly=False)
    edi_payroll_enable_validate_state = fields.Boolean(related="company_id.edi_payroll_enable_validate_state",
                                                       string="Enable intermediate 'DIAN Validation' state for payroll",
                                                       default=False, readonly=False)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res['edi_payroll_is_not_test'] = self.env.company.edi_payroll_is_not_test
        res['edi_payroll_enable'] = self.env.company.edi_payroll_enable
        res['edi_payroll_consolidated_enable'] = self.env.company.edi_payroll_consolidated_enable
        res['edi_payroll_always_validate'] = self.env.company.edi_payroll_always_validate
        res['edi_payroll_enable_validate_state'] = self.env.company.edi_payroll_enable_validate_state
        return res
