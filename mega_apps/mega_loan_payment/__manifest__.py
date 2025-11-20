{
    "name": "Mega - Loan Payment",
    "summary": "Loan payments (principal + interest) from the loan",
    "version": "1.0",
    "author": "Jorge Alberto Quiroz Sierra",
    "website": "https://mega.realnet.com.co/",
    "sequence": -107,
    "category": "MegaTecnicentro/LoanPayment",
    "depends": [
      "account",
      "account_loans"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_loan_views.xml",
        "wizard/loan_register_payment_wizard_views.xml",
        "wizard/payment_client_register_wizard_views.xml",
    ],
    "application": True,
    "installable": True,
    "license": "LGPL-3"
}
