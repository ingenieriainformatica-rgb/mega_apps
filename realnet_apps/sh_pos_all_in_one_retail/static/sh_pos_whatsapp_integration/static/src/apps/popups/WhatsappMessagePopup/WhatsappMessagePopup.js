/** @odoo-module */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class WhatsappMessagePopup extends Component {
    static template = "sh_pos_all_in_one_retail.WhatsappMessagePopup";    
    static components = { Dialog };
    
    confirm(){
        var self = this
        var text_msg = $('textarea[name="message"]').val();
        var mobile = $(".mobile_no").val();
        if (text_msg && mobile) {
            var href = "https://web.whatsapp.com/send?l=&phone=" + mobile + "&text=" + text_msg.replace('&','%26');
            $(".wp_url").attr("href", href);
            $(".wp_url span").trigger("click");
        } else {
            alert("Please Enter Message")
        }
    }
}
