{
    "name": "MEGA - Reglas salariales Payroll",
    "summary": "Reglas salariales básicas para nómina",
    "version": "1.0",
    "sequence": -130,
    "website": "https://mega.realnet.com.co/",
    "author": "Jorge Alberto Quiroz Sierra",
    "category": "MegaTecnicentro/Payroll",
    "depends": [
        "hr_payroll",
    ],
    "data": [
        "views/mega_hr_payslip_line_hide.xml",
        "rules/payroll_rules.xml",
        "type/mega_payslip_input_types.xml",
    ],
    "application": True,
    "installable": True,
    "license": "LGPL-3",
}
