{
    "name": "Sale and purchasing override",
    "version": "1.0",
    "summary": "Update accounts tools",
    "author": "Jorge Alberto Quiroz Sierra",
    "category": "MegaTecnicentro/SalePurchasing",
    "website": "https://mega.realnet.com.co/",
    "depends": [
        "purchase", 
        "sale_management", 
        "account"
    ],
    'sequence': -100,
    "data": [
        "security/realnet_partner_security.xml",
        "views/purchase_order_no_partner_create.xml",
        "views/sale_order_no_partner_create.xml",
        "views/sale_advance_payment_inv_no_choice.xml",
        "views/account_move_partner_bank_no_create.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": True,
}
