import logging
from odoo import fields, models, api  #type: ignore

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    smmlv_value = fields.Monetary("SMMLV", currency_field='currency_id', readonly=False)
    uvt_value = fields.Monetary("UVT", currency_field='currency_id', readonly=False)
    stm_value = fields.Monetary("Monthly transportation allowance", currency_field='currency_id', readonly=False)

    # Employee contribution rates
    salud_employee_rate = fields.Float(
        string="Salud trabajador (%)",
        default=4.0,
        help="Porcentaje de aporte a salud que descuenta al trabajador."
    )
    pension_employee_rate = fields.Float(
        string="Pensión trabajador (%)",
        default=4.0,
        help="Porcentaje de aporte a pensión que descuenta al trabajador."
    )

    # Employer contribution rates (🔥 nuevos campos)
    salud_employer_rate = fields.Float(
        string="Salud empleador (%)",
        default=8.5,
        help="Porcentaje de aporte a salud que asume el empleador."
    )
    pension_employer_rate = fields.Float(
        string="Pensión empleador (%)",
        default=12.0,
        help="Porcentaje de aporte a pensión que asume el empleador."
    )


    # times
    daily_overtime = fields.Float("% Daily overtime", readonly=False, default=25.0)
    overtime_night_hours = fields.Float("% Overtime night hours", readonly=False, default=75.0)
    hours_night_surcharge = fields.Float("% Hours night surcharge", readonly=False, default=35.0)
    sunday_holiday_daily_overtime = fields.Float("% Sunday and Holiday daily overtime", readonly=False,
                                                 default=100.0)
    daily_surcharge_hours_sundays_holidays = fields.Float("% Daily surcharge hours on sundays and holidays",
                                                          readonly=False, default=75.0)
    sunday_night_overtime_holidays = fields.Float("% Sunday night overtime and holidays", readonly=False,
                                                  default=150.0)
    sunday_holidays_night_surcharge_hours = fields.Float("% Sunday and holidays night surcharge hours",
                                                         readonly=False, default=110.0)

    # Test
    edi_payroll_is_not_test = fields.Boolean(string="Production environment", default=False, readonly=False)

    # Enable/disable electronic payroll for company
    edi_payroll_enable = fields.Boolean(string="Enable electronic payroll for this company", default=False,
                                        readonly=False)

    # Test
    edi_payroll_test_set_id = fields.Char(string="TestSetId")

    # Software ID and pin
    edi_payroll_id = fields.Char(string="Software ID", readonly=False)
    edi_payroll_pin = fields.Char(string="Software PIN", readonly=False)

    # Consolidated payroll
    edi_payroll_consolidated_enable = fields.Boolean(string="Enable consolidated electronic payroll for this company",
                                                     default=False, readonly=False)

    # DIAN validation
    edi_payroll_always_validate = fields.Boolean(string="Always validate payslips", default=False)
    edi_payroll_enable_validate_state = fields.Boolean(string="Enable intermediate 'DIAN Validation' state for payroll",
                                                       default=False)
