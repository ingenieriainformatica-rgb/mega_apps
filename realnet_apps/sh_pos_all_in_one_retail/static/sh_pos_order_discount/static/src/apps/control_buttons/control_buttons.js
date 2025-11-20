/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { GlobalDiscountPopupWidget } from "@sh_pos_all_in_one_retail/static/sh_pos_order_discount/apps/popups/GlobalDiscountPopupWidget/GlobalDiscountPopupWidget";

patch(ControlButtons.prototype, {
    async onClickGlobalDiscount() {
        var self = this
        if (
            this.pos.get_order().get_orderlines() &&
            this.pos.get_order().get_orderlines().length > 0
        ) {
            this.pos.is_global_discount = true;
            self.dialog.add(GlobalDiscountPopupWidget, {
                title: 'Global Discount',
                body: "",
            })
        } else {
            alert("Add Product In Cart.");
        }
    },
    async onClickRemoveDiscount(){
        var orderlines = this.pos.get_order().get_orderlines();
        if (orderlines) {
        for (let each_orderline of orderlines) {
            each_orderline.set_discount(0);
            each_orderline.set_global_discount(0);
        }
        this.pos.get_order().set_order_global_discount(0.0);
        }
    }
});
