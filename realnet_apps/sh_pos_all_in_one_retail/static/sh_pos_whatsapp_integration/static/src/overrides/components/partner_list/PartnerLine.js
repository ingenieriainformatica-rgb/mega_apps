/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";// import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { WhatsappMessagePopup } from "@sh_pos_all_in_one_retail/static/sh_pos_whatsapp_integration/apps/popups/WhatsappMessagePopup/WhatsappMessagePopup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(PartnerLine.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
        this.dialog = useService("dialog");
    },
    async on_click_send_wp(event) {
        var message = "";
        if (this.pos.user.sign) {
            message += "%0A%0A%0A" + this.env.services.pos.user.sign;
        }
        const partner = this.props.partner;
        if(partner.mobile){
            this.dialog.add(WhatsappMessagePopup, {
                title: 'Send Whatsapp Message',
                mobile_no: partner.mobile,
                message: message.replace('&','%26'),
                confirmText: "Send",
                cancelText: "Cancel",
            });
        }

        else{
            this.dialog.add(AlertDialog, {
                title: _t("Mobile Number Not Found"),
                body: _t(
                    "Please Enter mobile number for this partner"
                ),
            });
        }
       
    }
})
