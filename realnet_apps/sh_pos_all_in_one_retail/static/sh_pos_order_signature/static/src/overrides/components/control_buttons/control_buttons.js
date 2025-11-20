/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { TemplateAddSignaturePopupWidget } from "@sh_pos_all_in_one_retail/static/sh_pos_order_signature/apps/popups/template_add_signature_popup/template_add_signature_popup";


patch(ControlButtons.prototype, {
    onClickSignature(){
        this.dialog.add(TemplateAddSignaturePopupWidget, {
            title: 'Add Signature',
        });
    }
});
