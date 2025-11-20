/** @odoo-module */

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { WhatsappMessagePopup } from "@sh_pos_all_in_one_retail/static/sh_pos_whatsapp_integration/apps/popups/WhatsappMessagePopup/WhatsappMessagePopup";

patch(ReceiptScreen.prototype, {

    async onClickSendWpDirect(event) {
        var message = "";
        var self = this;

        const partner = this.currentOrder.get_partner();
        if (partner.mobile) {
            var mobile = partner.mobile;
            var order = this.currentOrder;
            var receipt = this.currentOrder.export_for_printing();
            var orderlines = this.currentOrder.get_orderlines();
            message +=
                "Dear " +
                partner.name +
                "," +
                "%0A%0A" +
                "Here is the order " +
                "*" +
                receipt.name +
                "*" +
                " amounting in " +
                "*" +
                self.env.utils.formatCurrency(parseFloat(receipt.amount_total.toFixed(2))) +
                "*" +
                " from " +
                self.pos.company.name +
                "%0A%0A";
            if (receipt.orderlines.length > 0) {
                message += "Following is your order details." + "%0A";
                for (const orderline of receipt.orderlines) {
                        message += "%0A" + "*" + orderline.productName + "*" + "%0A" + "*Qty:* " + orderline.qty + "%0A" + "*Price:* " + orderline.price +  "%0A";
                        if (orderline.discount > 0) {
                            message += "*Discount:* " + orderline.discount + "%25" + "%0A";
                        }
                };
                message += "________________________" + "%0A";
            }
            message += "*" + "Total Amount:" + "*" + "%20" + self.env.utils.formatCurrency(parseFloat(receipt.amount_total.toFixed(2)));
            if (this.pos.user.sign) {
                message += "%0A%0A%0A" + this.pos.user.sign;
            }
            $(".default-view").append('<a class="wp_url" target="blank" href=""><span></span></a>');
            var href = "https://web.whatsapp.com/send?l=&phone=" + mobile + "&text=" + message.replace('&','%26');
            $(".wp_url").attr("href", href);
            $(".wp_url span").trigger("click");
        }
        else{
            this.dialog.add(AlertDialog, {
                title: _t("Mobile Number Not Found"),
                body: _t(
                    "Please Enter mobile number for this partner"
                ),
            });
        }
    },
    async onClickSendWp(event) {
        var message = "";
        var self = this;
        const partner = this.currentOrder.get_partner();
        if (partner && partner.mobile) {
            var mobile = partner.mobile;
            var receipt = this.currentOrder.export_for_printing();
        
            message +=
                "Dear " +
                partner.name +
                "," +
                "%0A%0A" +
                "Here is the order " +
                "*" +
                receipt.name +
                "*" +
                " amounting in " +
                "*" +
                self.env.utils.formatCurrency(parseFloat(receipt.amount_total.toFixed(2))) +
                "*" +
                " from " +
                self.pos.company.name +
                "%0A%0A";
            if (receipt.orderlines.length > 0) {
                message += "Following is your order details." + "%0A";
                for (const orderline of receipt.orderlines) {
                    message += "%0A" + "*" + orderline.productName + "*" + "%0A" + "*Qty:* " + orderline.qty + "%0A" + "*Price:* " + orderline.price +  "%0A";
                    if (orderline.discount > 0) {
                        message += "*Discount:* " + orderline.discount + "%25" + "%0A";
                    }
                };
                message += "________________________" + "%0A";
            }
            message += "*" + "Total Amount:" + "*" + "%20" + self.env.utils.formatCurrency(parseFloat(receipt.amount_total.toFixed(2)));
            if (this.pos.user.sign) {
                message += "%0A%0A%0A" + this.pos.user.sign;
            }
            const { confirmed } = this.dialog.add(WhatsappMessagePopup, {
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

});
