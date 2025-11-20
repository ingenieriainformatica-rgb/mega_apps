# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.
{
    "name": "Point of Sale Retail Shop| POS Retail Shop| All In One POS Retail",         
    "author": "Softhealer Technologies",     
    "website": "https://www.softhealer.com",     
    "support": "support@softhealer.com",     
    "category": "Point of Sale",   
    "version": "0.0.9",       
    "summary": """Retail Point Of Sale Solution Retail POS cash in cash out own customer discount mass update product tags own product template auto validate pos quick print receipt import pos secondary product suggestion pos access right pos auto lock cancel whatsapp return exchange pos all feature Restaurant & Shop Retail All In One POS Enterprise POS Community All In One POS all in one features pos Reorder pos Reprint pos Coupon Discount pos Order Return pos order all pos all features pos discount pos order list print pos receipt pos item count retail pos retail import sale from pos create quote from pos odoo All in one pos Reprint pos Return POS Stock pos gift import sale from pos multi currency payment pos pay later pos internal transfer pos disable payment pos product template pos product operation pos loyalty rewards all pos reports pos stock pos retail pos label pos cash control pos cash in out pos cash out pos logo pos receipt all pos in one all pos in one retail  odoo All in One Point of Sale Point of Sale Features POS Features Product Multi barcode for POS POS Multi barcode Discount in POS Customer DIscount Point of sale POS Category Slider Point of Sale category slider Import POS Order from Excel Import POS Order from CSV Import Multiple POS Orders Import Multiple POS Orders from Excel Import Multiple POS Orders from CSV POS Realtime Quantity Update POS Realtime Qty Update POS Realtime Stock Update Realtime Stock Update POS Disable Button Option POS Disable Button Feature Disable Button POS POS Hide Button Disable Button Access Create PO from POS Create Purchase Order from POS Create PO from Point of Sale Create Purchase Order from Point of Sale Generate Purchase Order from POS Request for Quotation from POS Request for Quotation from Point of Sale RFQ from POS RFQ from Point of Sale Create Purchase Order POS Product Variants Popup POS all in one features pos Reorder pos Reprint pos Coupon Discount pos Order Return POS Stock pos gift pos order all pos all features pos discount pos order list print pos receipt pos item count retail pos retail import sale from pos create quote from pos Point of Sale Product Variants Popup POS Product Multi Variants Select Product Variants Product Variant Suggestion POS Orderlist Filter Point of Sale Orderlist Filter Orderlist Filter in POS Order list Filter Point of Sale Order list Filter Order list Filter In POS SO from POS Sale order from POS Sale order from Point of Sale SO from Point of Sale Quotation form POS Quotation form Point of Sale Generate Sale Order from POS Generate Quotation from POS POS Product Suggestion POS Related Products Point of Sale Product Suggestion Pos Recommended products  Dsiplay Related Product  POS Product Weight and Volume POS Product Weight  POS Product Volume POS Product Volume information POS Product Weight Information POS Product Weight Details POS Product Volume Details Point Of Sale Secondary Unit Of Measure POS multiple UOM POS multiple Unit of Measure Product Unit of Measure Multiple Unit of Measure POS Product Bundle Sale Combo Combo of Product Bundle of products Pack of Products Combine two or more Products in POS Access Rights in POS POS Access Rights Disable Discount Button  Disable Price Button  Disable Plus minus Button  Disable Payment Button  Restrict Numpad Auto Lock POS POS Screen Auto Lock Auto Lock Screen POS Session Lock Auto Lock POS Bag Charges POS Carry Bag Charges POS Carry Bag Option Bag Charges Carry Bag Charges Carry Bag Option POS Bag Size Option Add Bag Charges Add Carry Bag Charges Cancel POS Orders Cancel Point of Sale Order POS Order Cancellation Cancel Order Delet POS Order POS Chatter Add Chatter in POS Add Chatter in Point of Sale Point of Sale Chatter Chatter History POS Chatbot Point of Sale Chatbot POS Item Counter Item Counter Point of Sale Product Counter POS Product Couter POS Item Calculator POS Product Count POS Default Customer Point of Sale Default Customer POS Default Invoice Point of Sale Default Invoice Point of Sale Default Customer Invoice POS Default Customer Invoice POS Bydefault Customer POS Bydefault Invoice POS Login POS Direct Login POS Signin POS Direct Sign in POS Keyboard Shortcut Custom Keyboard POS Custom Keyboard POS Shortcut Key Access POS Shortcut POS Pricelist POS Logo Point of Sale Logo POS Custom Logo POS Notes POS Line Notes Point of Sale Order Line Notes Point of Sale Order List POS Remove Cart Item Point of Sale Remove Cart Item Point of Sale Cart Item Remove POS Item Remove POS Clear Cart POS Delet Cart Item POS Cart Clear Remove Cart Item POS Rounding POS Rounding Amount POS Rounding Enable Point of Sale Rounding Cash Rounding Rounding Payment Rounding Rounding Off POS Customisation POS Customization Point of Sale Customization POS Stock Display POS Stock Quantity  POS on Hand Quantity POS Inventory Stock Quantity POS Forecasted Quantity POS Incoming Quanity POS Whatsapp Integration Whatsapp Inetegration Point of Sale Whatsapp Integration POS Own Customer POS Specific customer Salesperson specific customer POS Special Customer User Own Customer POS User Own Customer POS User wise Customer POS Own Product POS Specific Product POS User Specific Product POS User own Product POS Saleperson Specific Product POS Product Tags Point of Sale Product Tags POS Product Search by Tags POS Tags Search Product Tags Search Auto Validate Point of Sale POS Auto Validate  Auto Validate  Auto POS Session Auto Validate POS Session POS Order Product Template Product Custom Template POS Product Template Build POS Product Multiple Template POS Product Variants POS Product Multiple Variants Merge Categories POS Categories Merge POS Merge Categories Point of Sale Discount POS Custom Discount POS Sale Line Discount POS Discount Odoo POS Receipt With Discount Employee Discount POS Employee Discount Product Code POS Product Code MAnage Product Code Product Quantity Pack Product Pack Product Package Product Bundle Product Combo POS Product Pack Customize Product Pack Customize Product Bundle POS Section Point of Sale Label POS Order Label POS Category POint of Sale Cart Line Label POS Cart Line LAbel POS exchange POS Return and exchange POS Order Exchange Point of Sale Order Exchange Point of Sale Order Return Manage Return Manage Exchange POS Product Return POS Product Exchange POS Product Return Odoo POS Refund POS All in one pos all in one pos point of sale all in one point of sale Odoo What Is a Retail POS Solution What Is a Retail Point Of Sale Solution Retail POS System Retail Point Of Sale System Retail Point of Sale Software Retail POS Software Top Retail POS Systems Top Retail Point Of Sale Systems Best Retail POS Best Point Of Sale Retail Best Retail Point Of Sale POS All In One Point of sales All In One POS Responsive POS Order History POS Order List POS Bundle POS Signature POS Keyboard Shortcut POS Direct Login POS Toppings POS Orders With Type POS Order Type""",          
    "description": """ This is the fully retail solution for any kind of retail shop or bussiness.  """,
    "depends": ["point_of_sale", 'hr',"utm", "portal"],
    'external_dependencies': {
        'python': ['xlrd'],
    },
    "data": [

        "sh_pos_theme_responsive/data/pos_theme_settings_data.xml",
        "sh_pos_theme_responsive/security/ir.model.access.csv",
        "sh_pos_theme_responsive/views/sh_pos_theme_settings_views.xml",

        "sh_auto_validate_pos/data/cron_view.xml",
        "sh_auto_validate_pos/security/ir.model.access.csv",
        "sh_auto_validate_pos/views/log_track_view.xml",

        
        'sh_pos_keyboard_shortcut/security/ir.model.access.csv',
        'sh_pos_keyboard_shortcut/data/sh_keyboard_key_data.xml',
        
        'views/res_config_setting_views.xml',

        "sh_pos_cancel/security/pos_security.xml",
        "sh_pos_cancel/data/server_action_data.xml",
        "sh_pos_cancel/views/pos_order_views.xml",

        # varaint
        'sh_pos_product_variant/views/product_template.xml',

        # # product suggtion
        "pos_product_suggestion/security/ir.model.access.csv",
        'pos_product_suggestion/views/product_view.xml',

        'sh_pos_cash_in_out/views/cash_in_out_menu.xml',
        'sh_pos_cash_in_out/security/ir.model.access.csv',

        'sh_base_order_type/security/ir.model.access.csv',
        'sh_pos_order_type/views/sh_order_type_views.xml',
        'sh_pos_order_type/views/pos_order_views.xml',

        'sh_product_multi_barcode/security/ir.model.access.csv',
        'sh_product_multi_barcode/views/product_product_views.xml',
        'sh_product_multi_barcode/views/product_template_views.xml',
        'sh_product_multi_barcode/views/res_config_settings.xml',

        'sh_pos_weight/views/pos_order_view.xml',

        'sh_pos_order_signature/views/pos_order_view.xml',

        'sh_pos_own_products/views/product.xml',

        'sh_pos_own_customers/views/res_partner.xml',

        'sh_pos_receipt/security/sh_pos_receipt_groups.xml',
        'sh_pos_receipt/report/pos_order_reports.xml',
        'sh_pos_receipt/data/mail_template_data.xml',
        'sh_pos_receipt/report/pos_order_templates.xml',
        'sh_pos_receipt/views/pos_order_views.xml',

        'sh_pos_customer_maximum_discount/views/res_partner_views.xml',

        "sh_pos_reports/sh_pos_z_report/security/ir.model.access.csv",
        "sh_pos_reports/sh_pos_z_report/views/pos_config_views.xml",
        # "sh_pos_reports/sh_pos_z_report/views/res_config_settings_views.xml",
        "sh_pos_reports/sh_pos_z_report/reports/pos_z_report_detail.xml",
        "sh_pos_reports/sh_pos_z_report/reports/report_zdetails.xml",
        "sh_pos_reports/sh_pos_z_report/views/pos_session_z_report.xml",
        "sh_pos_reports/sh_pos_z_report/wizard/pos_z_report_wizard.xml",
        "sh_pos_reports/sh_pos_z_report/views/res_users_views.xml",
        "sh_pos_reports/sh_pos_z_report/views/hr_employee_views.xml",

        'sh_pos_reports/sh_day_wise_pos/security/day_wise_report.xml',
        'sh_pos_reports/sh_day_wise_pos/security/ir.model.access.csv',
        'sh_pos_reports/sh_day_wise_pos/views/sh_day_wise_pos_views.xml',
        'sh_pos_reports/sh_day_wise_pos/wizard/sh_pos_order_report_views.xml',
        'sh_pos_reports/sh_day_wise_pos/report/sh_day_wise_pos_report_templates.xml',

        "sh_pos_reports/sh_payment_pos_report/security/sh_payment_pos_report_groups.xml",
        "sh_pos_reports/sh_payment_pos_report/security/ir.model.access.csv",
        "sh_pos_reports/sh_payment_pos_report/wizard/sh_pos_payment_report_wizard_views.xml",
        "sh_pos_reports/sh_payment_pos_report/report/sh_payment_pos_report_templates.xml",
        'sh_pos_reports/sh_payment_pos_report/views/sh_payment_report_views.xml',

        "sh_pos_reports/sh_pos_report_user/security/sh_pos_report_user.xml",
        "sh_pos_reports/sh_pos_report_user/security/ir.model.access.csv",
        "sh_pos_reports/sh_pos_report_user/wizard/sh_pos_report_user_wizard_views.xml",
        "sh_pos_reports/sh_pos_report_user/report/sh_pos_report_user_report_templates.xml",
        "sh_pos_reports/sh_pos_report_user/views/sh_pos_report_user_views.xml",

        "sh_pos_reports/sh_top_pos_customer/security/ir.model.access.csv",
        "sh_pos_reports/sh_top_pos_customer/wizard/sh_tc_pos_top_customer_wizard_views.xml",
        "sh_pos_reports/sh_top_pos_customer/report/sh_top_pos_customer_report_templates.xml",
        "sh_pos_reports/sh_top_pos_customer/views/sh_top_pos_customer_views.xml",

        "sh_pos_reports/sh_top_pos_product/security/ir.model.access.csv",
        "sh_pos_reports/sh_top_pos_product/wizard/sh_tsp_top_pos_product_wizard_views.xml",
        "sh_pos_reports/sh_top_pos_product/views/sh_tsp_top_pos_product_views.xml",
        "sh_pos_reports/sh_top_pos_product/report/top_pos_product_report.xml",

        "sh_pos_reports/sh_pos_profitability_report/security/sh_pos_profitibility_report_groups.xml",
        "sh_pos_reports/sh_pos_profitability_report/report/pos_order_line_views.xml",

        'sh_pos_reports/sh_customer_pos_analysis/security/ir.model.access.csv',
        'sh_pos_reports/sh_customer_pos_analysis/report/sh_customer_pos_analysis_report_templates.xml',
        'sh_pos_reports/sh_customer_pos_analysis/wizard/sh_pos_analysis_wizard_views.xml',
        'sh_pos_reports/sh_customer_pos_analysis/views/sh_customer_pos_analysis_views.xml',

        'sh_pos_reports/sh_pos_by_category/security/pos_by_category.xml',
        'sh_pos_reports/sh_pos_by_category/security/ir.model.access.csv',
        'sh_pos_reports/sh_pos_by_category/report/sh_pos_by_category_report_templates.xml',
        'sh_pos_reports/sh_pos_by_category/wizard/sh_pos_category_wizard_views.xml',
        'sh_pos_reports/sh_pos_by_category/views/sh_pos_by_product_category_views.xml',

        "sh_pos_reports/sh_pos_invoice_summary/security/ir.model.access.csv",
        "sh_pos_reports/sh_pos_invoice_summary/report/sh_pos_inv_summary_doc_report_templates.xml",
        "sh_pos_reports/sh_pos_invoice_summary/wizard/sh_pos_inv_summary_wizard_views.xml",
        "sh_pos_reports/sh_pos_invoice_summary/views/sh_pos_invoice_summary_views.xml",

        "sh_pos_reports/sh_pos_product_profit/security/ir.model.access.csv",
        "sh_pos_reports/sh_pos_product_profit/report/sh_pos_product_profit_doc_report_templates.xml",
        "sh_pos_reports/sh_pos_product_profit/wizard/sh_pos_product_profit_wizard_views.xml",
        "sh_pos_reports/sh_pos_product_profit/views/sh_pos_product_profit_views.xml",

        "sh_pos_reports/sh_product_pos_indent/security/ir.model.access.csv",
        "sh_pos_reports/sh_product_pos_indent/report/sh_pos_product_indent_doc_report_templates.xml",
        "sh_pos_reports/sh_product_pos_indent/wizard/sh_pos_product_indent_wizard_views.xml",
        "sh_pos_reports/sh_product_pos_indent/views/sh_product_pos_indent_views.xml",

        'sh_pos_reports/sh_pos_sector_report/security/ir.model.access.csv',
        'sh_pos_reports/sh_pos_sector_report/wizard/sh_pos_section_report_wizard_views.xml',
        'sh_pos_reports/sh_pos_sector_report/views/sh_pos_sector_views.xml',

        'sh_pos_order_return_exchange/views/product_template.xml',

        "sh_pos_whatsapp_integration/views/res_users.xml",

        'sh_pos_order_label/data/data.xml',
        'sh_pos_order_label/views/pos_order.xml',

        'sh_pos_note/views/pos_order.xml',

        "sh_message/security/ir.model.access.csv",
        "sh_message/wizard/sh_message_wizard.xml",

        'sh_import_pos/security/import_pos_groups.xml',
        'sh_import_pos/security/ir.model.access.csv',
        'sh_import_pos/wizard/import_pos_wizard_views.xml',
        'sh_import_pos/views/pos_views.xml',

        'sh_pos_direct_login/views/res_users.xml',

        'sh_pos_product_template/security/ir.model.access.csv',
        'sh_pos_product_template/views/pos_template_product.xml', 

        'sh_pos_product_toppings/security/ir.model.access.csv',
        'sh_pos_product_toppings/views/pos_category_views.xml',
        'sh_pos_product_toppings/views/product_product_views.xml',
        'sh_pos_product_toppings/views/sh_product_toppings.xml',
        'sh_pos_product_toppings/views/sh_topping_group.xml',

        'sh_pos_rounding/data/data.xml',

    ],
    # 'demo': [
    #     'sh_pos_keyboard_shortcut/demo/sh_pos_keyboard_shortcut_demo.xml',
    # ],
    'assets': {
         'point_of_sale.customer_display_assets': {
            "sh_pos_all_in_one_retail/static/sh_pos_product_toppings/static/src/overrides/components/customer_display/customer_display_template.xml",

        },
        'point_of_sale._assets_pos': [
            'web/static/lib/jquery/jquery.js',
            # # theme
            "/sh_pos_all_in_one_retail/static/sh_pos_theme_responsive/static/src/overrides/pos_theme_variables.scss",
            'sh_pos_all_in_one_retail/static/sh_pos_theme_responsive/static/src/scss/mixin.scss',
            'sh_pos_all_in_one_retail/static/sh_pos_theme_responsive/static/src/scss/pos_common.scss',
            "sh_pos_all_in_one_retail/static/sh_pos_theme_responsive/static/src/overrides/scss/theme_style_1&2&3/theme_style_1&2&3.scss",
            "sh_pos_all_in_one_retail/static/sh_pos_theme_responsive/static/src/overrides/scss/theme_style_4/theme_style_4.scss",
            "sh_pos_all_in_one_retail/static/sh_pos_theme_responsive/static/src/overrides/scss/other_condition/other_condition.scss",
            'sh_pos_all_in_one_retail/static/sh_pos_theme_responsive/static/lib/owl.carousel.js',
            'sh_pos_all_in_one_retail/static/sh_pos_theme_responsive/static/lib/owl.carousel.css',
            'sh_pos_all_in_one_retail/static/sh_pos_theme_responsive/static/lib/owl.theme.default.min.css',
            'sh_pos_all_in_one_retail/static/sh_pos_theme_responsive/static/src/overrides/**/*',
            
            # pos counter
            'sh_pos_all_in_one_retail/static/sh_pos_counter/**/*',

            # # create sale order from pos
            'sh_pos_all_in_one_retail/static/sh_pos_create_so/static/src/**/*',

            # Create purchase order from pos
            'sh_pos_all_in_one_retail/static/sh_pos_create_po/static/src/**/*',

            # order list
            'sh_pos_all_in_one_retail/static/sh_pos_order_list/static/**/*',
            
            # pos_product_suggestion
            
            'sh_pos_all_in_one_retail/static/pos_product_suggestion/static/src/**/*',
            
            # receipt extend
            'sh_pos_all_in_one_retail/static/sh_pos_receipt_extend/static/src/**/*',

            # variant merge
            'sh_pos_all_in_one_retail/static/sh_pos_product_variant/static/src/**/*',

            # Wh stock
            'sh_pos_all_in_one_retail/static/sh_pos_wh_stock/static/src/app/**/*',
            'sh_pos_all_in_one_retail/static/sh_pos_wh_stock/static/src/scss/**/*',

            # remove cart item
            'sh_pos_all_in_one_retail/static/sh_pos_remove_cart_item/static/src/**/*',

            # discount
            
            'sh_pos_all_in_one_retail/static/sh_pos_order_discount/static/src/**/*',

            # suggestion
            'sh_pos_all_in_one_retail/static/pos_product_suggestion/static/src/**/*',

            'sh_pos_all_in_one_retail/static/sh_pos_product_code/static/src/**/*',

            'sh_pos_all_in_one_retail/static/sh_pos_cash_in_out/static/src/**/*',

            'sh_pos_all_in_one_retail/static/sh_pos_order_type/static/**/*',
            'sh_pos_all_in_one_retail/static/sh_pos_multi_barcode/static/src/overrides/**/*',            

            # default customer
            'sh_pos_all_in_one_retail/static/sh_pos_default_customer/static/**/*',

            # default invoice
            'sh_pos_all_in_one_retail/static/sh_pos_default_invoice/static/**/*',

            # auto lock
            'sh_pos_all_in_one_retail/static/sh_pos_auto_lock/static/**/*',

            #fronted cancel
            'sh_pos_all_in_one_retail/static/sh_pos_fronted_cancel/static/src/apps/Screens/*',

            #pos weight
            'sh_pos_all_in_one_retail/static/sh_pos_weight/static/src/overrides/models/model.js',
            'sh_pos_all_in_one_retail/static/sh_pos_weight/static/src/overrides/components/orderline/orderline.xml',
            'sh_pos_all_in_one_retail/static/sh_pos_weight/static/src/overrides/components/orderline/orderline.js',
            'sh_pos_all_in_one_retail/static/sh_pos_weight/static/src/overrides/components/order_receipt/order_receipt.xml',
            'sh_pos_all_in_one_retail/static/sh_pos_weight/static/src/overrides/components/product_screen/product_screen.xml',
            'sh_pos_all_in_one_retail/static/sh_pos_weight/static/src/scss/pos.scss',

            #pos order signature
            'web/static/lib/signature_pad/signature_pad.umd.js',
            'sh_pos_all_in_one_retail/static/sh_pos_order_signature/static/src/apps/popups/template_add_signature_popup/template_add_signature_popup.js',
            'sh_pos_all_in_one_retail/static/sh_pos_order_signature/static/src/apps/popups/template_add_signature_popup/template_add_signature_popup.xml',
            'sh_pos_all_in_one_retail/static/sh_pos_order_signature/static/src/overrides/components/control_buttons/control_buttons.js',
            'sh_pos_all_in_one_retail/static/sh_pos_order_signature/static/src/overrides/components/control_buttons/control_buttons.xml',
            'sh_pos_all_in_one_retail/static/sh_pos_order_signature/static/src/overrides/models/models.js',
            'sh_pos_all_in_one_retail/static/sh_pos_order_signature/static/src/overrides/components/order_receipt/order_receipt.xml',
            'sh_pos_all_in_one_retail/static/sh_pos_order_signature/static/src/scss/sh_custom.scss',

            #own products
            'sh_pos_all_in_one_retail/static/sh_pos_own_products/static/src/overrides/products_widget.js',

            #own customers
            'sh_pos_all_in_one_retail/static/sh_pos_own_customers/static/src/js/Screens/partner_list_screen.js',

            #pos shortcut
            'sh_pos_all_in_one_retail/static/sh_pos_keyboard_shortcut/static/src/**/*',

            'sh_pos_all_in_one_retail/static/sh_pos_customer_maximum_discount/static/src/overrides/components/partner_list/PartnerLine.xml',
            'sh_pos_all_in_one_retail/static/sh_pos_customer_maximum_discount/static/src/overrides/components/partner_list/PartnerList.xml',
            'sh_pos_all_in_one_retail/static/sh_pos_customer_maximum_discount/static/src/overrides/components/partner_list/PosStore.js',
            'sh_pos_all_in_one_retail/static/sh_pos_customer_maximum_discount/static/src/scss/pos.scss',

            'sh_pos_all_in_one_retail/static/sh_pos_reports/sh_pos_z_report/static/src/overrides/components/control_buttons/control_buttons.xml',
            'sh_pos_all_in_one_retail/static/sh_pos_reports/sh_pos_z_report/static/src/overrides/components/control_buttons/control_buttons.js',
            'sh_pos_all_in_one_retail/static/sh_pos_reports/sh_pos_z_report/static/src/app/Popups/ZReportOptionPopup/ZReportOptionPopup.js',
            'sh_pos_all_in_one_retail/static/sh_pos_reports/sh_pos_z_report/static/src/app/Popups/ZReportOptionPopup/ZReportOptionPopup.xml',
            'sh_pos_all_in_one_retail/static/sh_pos_reports/sh_pos_z_report/static/src/app/Popups/ZReportOptionPopup/ZReportOptionPopup.scss',
            'sh_pos_all_in_one_retail/static/sh_pos_reports/sh_pos_z_report/static/src/app/Popups/ZReportPostedSessionOptionPopup/ZReportPostedSessionOptionPopup.js',
            'sh_pos_all_in_one_retail/static/sh_pos_reports/sh_pos_z_report/static/src/app/Popups/ZReportPostedSessionOptionPopup/ZReportPostedSessionOptionPopup.xml',
            'sh_pos_all_in_one_retail/static/sh_pos_reports/sh_pos_z_report/static/src/app/Popups/ZReportPostedSessionOptionPopup/ZReportPostedSessionOptionPopup.scss',
            'sh_pos_all_in_one_retail/static/sh_pos_reports/sh_pos_z_report/static/src/overrides/components/receipt_screen/**/*',
            'sh_pos_all_in_one_retail/static/sh_pos_reports/sh_pos_z_report/static/src/overrides/models/model.js',

            'sh_pos_all_in_one_retail/static/sh_pos_order_return_exchange/static/src/apps/popups/return_order_popup/return_order_popup.js',
            'sh_pos_all_in_one_retail/static/sh_pos_order_return_exchange/static/src/apps/popups/return_order_popup/return_order_popup.xml',
            'sh_pos_all_in_one_retail/static/sh_pos_order_return_exchange/static/src/apps/screens/order_list_screen/order_list_screen.js',
            'sh_pos_all_in_one_retail/static/sh_pos_order_return_exchange/static/src/apps/screens/order_list_screen/order_list_screen.xml',
            'sh_pos_all_in_one_retail/static/sh_pos_order_return_exchange/static/src/apps/screens/order_list_screen/order_list_screen.scss',                                                          

            'sh_pos_all_in_one_retail/static/sh_pos_whatsapp_integration/static/src/overrides/**/*',
            'sh_pos_all_in_one_retail/static/sh_pos_whatsapp_integration/static/src/apps/**/*',
            'sh_pos_all_in_one_retail/static/sh_pos_whatsapp_integration/static/src/scss/**/*',

            'sh_pos_all_in_one_retail/static/sh_pos_order_label/static/src/app/control_buttons/Add_label_button/*',
            'sh_pos_all_in_one_retail/static/sh_pos_order_label/static/src/app/labal_popup/*',
            'sh_pos_all_in_one_retail/static/sh_pos_order_label/static/src/overrides/models/pos_order_line.js',
            'sh_pos_all_in_one_retail/static/sh_pos_order_label/static/src/overrides/components/orderwidget/*',
            'sh_pos_all_in_one_retail/static/sh_pos_order_label/static/src/overrides/components/receipt_screen/order_receipt/order_receipt.xml',

            "sh_pos_all_in_one_retail/static/sh_pos_note/static/src/apps/screen/all_note_screen/**/*",
            "sh_pos_all_in_one_retail/static/sh_pos_note/static/src/overrides/components/control_buttons/control_buttons.js",
            "sh_pos_all_in_one_retail/static/sh_pos_note/static/src/overrides/components/control_buttons/control_buttons.xml",
            "sh_pos_all_in_one_retail/static/sh_pos_note/static/src/overrides/components/Order_receipt/order_receipt.xml",
            "sh_pos_all_in_one_retail/static/sh_pos_note/static/src/overrides/models/model.js",
            "sh_pos_all_in_one_retail/static/sh_pos_note/static/src/overrides/components/payment_screen/payment_screen.xml",
            "sh_pos_all_in_one_retail/static/sh_pos_note/static/src/overrides/components/payment_screen/payment_screen.js",
            "sh_pos_all_in_one_retail/static/sh_pos_note/static/src/overrides/components/text_input_popup/text_input_popup.js",
            "sh_pos_all_in_one_retail/static/sh_pos_note/static/src/overrides/components/text_input_popup/text_input_popup.xml",
            "sh_pos_all_in_one_retail/static/sh_pos_note/static/src/scss/pos.scss",

            'sh_pos_all_in_one_retail/static/sh_pos_direct_login/static/src/**/*',

            'sh_pos_all_in_one_retail/static/sh_pos_product_template/static/src/app/control_buttons/template_products_button/*',
            'sh_pos_all_in_one_retail/static/sh_pos_product_template/static/src/app/screen/**/*',
            'sh_pos_all_in_one_retail/static/sh_pos_product_template/static/src/scss/pos_custom.scss',
            'sh_pos_all_in_one_retail/static/sh_pos_product_template/static/src/overrides/models/pos_orderlines.js',

            "sh_pos_all_in_one_retail/static/sh_pos_line_pricelist/static/src/scss/pos.scss",
            'sh_pos_all_in_one_retail/static/sh_pos_line_pricelist/static/src/overrides/components/Orderline/orderline.xml',
            'sh_pos_all_in_one_retail/static/sh_pos_line_pricelist/static/src/overrides/models/model.js',
            'sh_pos_all_in_one_retail/static/sh_pos_line_pricelist/static/src/overrides/models/pos_store.js',
            'sh_pos_all_in_one_retail/static/sh_pos_line_pricelist/static/src/overrides/components/Orderline/orderline.js',
            'sh_pos_all_in_one_retail/static/sh_pos_line_pricelist/static/src/apps/pricelist_popup/pricelist_popup.js',
            'sh_pos_all_in_one_retail/static/sh_pos_line_pricelist/static/src/apps/pricelist_popup/pricelist_popup.xml',

            'sh_pos_all_in_one_retail/static/sh_pos_bag_charges/static/src/apps/popups/bag_category_list_popup/bag_category_list_popup.js',
            "sh_pos_all_in_one_retail/static/sh_pos_bag_charges/static/src/apps/popups/bag_category_list_popup/bag_category_list_popup.xml",
            'sh_pos_all_in_one_retail/static/sh_pos_bag_charges/static/src/apps/control_buttons/bag_charges_btn/bag_charges_btn.js',
            'sh_pos_all_in_one_retail/static/sh_pos_bag_charges/static/src/apps/control_buttons/bag_charges_btn/bag_charges_btn.xml',
            'sh_pos_all_in_one_retail/static/sh_pos_bag_charges/static/src/apps/scss/style.scss',

            "sh_pos_all_in_one_retail/static/sh_pos_order_return_exchange_barcode/static/src/apps/models.js",
            "sh_pos_all_in_one_retail/static/sh_pos_order_return_exchange_barcode/static/src/overrides/screens/product_screen.js",
            "sh_pos_all_in_one_retail/static/sh_pos_order_return_exchange_barcode/static/src/xml/pos.xml",
            "sh_pos_all_in_one_retail/static/sh_pos_order_return_exchange_barcode/static/src/scss/pos_order_return_exchange.scss",

            "sh_pos_all_in_one_retail/static/sh_pos_product_toppings/static/src/overrides/components/control_buttons/control_buttons.js",
            "sh_pos_all_in_one_retail/static/sh_pos_product_toppings/static/src/overrides/orderline/orderline.scss",
            "sh_pos_all_in_one_retail/static/sh_pos_product_toppings/static/src/overrides/components/control_buttons/control_buttons.xml",
            "sh_pos_all_in_one_retail/static/sh_pos_product_toppings/static/src/app/Popups/ToppingsPopup/ToppingsPopup.js",
            "sh_pos_all_in_one_retail/static/sh_pos_product_toppings/static/src/app/Popups/ToppingsPopup/ToppingsPopup.xml",
            "sh_pos_all_in_one_retail/static/sh_pos_product_toppings/static/src/overrides/models/PosOrderLine.js",
            "sh_pos_all_in_one_retail/static/sh_pos_product_toppings/static/src/overrides/orderline/orderline.xml",
            "sh_pos_all_in_one_retail/static/sh_pos_product_toppings/static/src/overrides/orderline/orderline.js",
            "sh_pos_all_in_one_retail/static/sh_pos_product_toppings/static/src/overrides/models/pos_store.js",
            "sh_pos_all_in_one_retail/static/sh_pos_product_toppings/static/src/overrides/components/order_summary/order_summary.js",
            # "sh_pos_all_in_one_retail/static/sh_pos_product_toppings/static/src/overrides/components/customer_display/customer_display_template.xml",
            "sh_pos_all_in_one_retail/static/sh_pos_product_toppings/static/src/scss/style.scss",

            'sh_pos_all_in_one_retail/static/sh_pos_rounding/static/src/scss/pos.scss',
            'sh_pos_all_in_one_retail/static/sh_pos_rounding/static/src/scss/sh_pos.scss',
            'sh_pos_all_in_one_retail/static/sh_pos_rounding/static/src/overrides/models/model.js',
            'sh_pos_all_in_one_retail/static/sh_pos_rounding/static/src/overrides/componenet/order_receipt/order_line.xml',
            'sh_pos_all_in_one_retail/static/sh_pos_rounding/static/src/overrides/componenet/order_receipt/order_receipt.xml',
            'sh_pos_all_in_one_retail/static/sh_pos_rounding/static/src/overrides/componenet/order_widget/order_widget.xml',
            'sh_pos_all_in_one_retail/static/sh_pos_rounding/static/src/overrides/componenet/payment_status/payment_status.js',
            'sh_pos_all_in_one_retail/static/sh_pos_rounding/static/src/overrides/componenet/payment_status/payment_status.xml',

            "sh_pos_all_in_one_retail/static/sh_pos_wh_stock_adv/static/src/app/store/models.js",
            # ('replace', 'sh_pos_all_in_one_retail/static/sh_pos_wh_stock/static/src/app/overrides/payment_screeen/payment_screen.js', 'sh_pos_all_in_one_retail/static/sh_pos_wh_stock_adv/static/src/app/overrides/screen/payment_screeen/payment_screen.js'),

            # Validación de crédito de cliente para consumidor final
            "sh_pos_all_in_one_retail/static/realnet_customer_credit_validation/static/src/overrides/models/pos_order.js",
            "sh_pos_all_in_one_retail/static/realnet_customer_credit_validation/static/src/overrides/components/payment_screen.js",

        ]
    },
    "images": [
        'static/description/splash-screen.gif',
        'static/description/splash-screen_screenshot.gif'

    ],
    "application": True,
    "auto_install": False,
    "license": "OPL-1",
    "price": 182.58,
    "currency": "EUR",
    "installable": True,
}
