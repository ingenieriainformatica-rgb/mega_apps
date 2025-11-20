/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";
import { ToppingsPopup } from "@sh_pos_all_in_one_retail/static/sh_pos_product_toppings/app/Popups/ToppingsPopup/ToppingsPopup";

patch(OrderSummary.prototype, {
    clickLine(ev, orderline) {
        if (this.pos.config.sh_enable_toppings && !orderline.isSelected() && !orderline.sh_is_topping){
            let Topping_products = []
            if (orderline.product_id.pos_categ_ids && orderline.product_id.pos_categ_ids.length > 0) {
                for (let category of orderline.product_id.pos_categ_ids) {
                    if (category && category.sh_product_topping_ids) {
                        Topping_products.push(...category.sh_product_topping_ids)
                    }
                }
            }
            if (orderline.product_id && orderline.product_id.sh_topping_ids && orderline.product_id.sh_topping_ids.length > 0) {
                for (let topping of orderline.product_id.sh_topping_ids) {
                    if (!Topping_products.includes(topping)) {
                        Topping_products.push(topping);
                    }
                }
            }
            if (Topping_products.length > 0) {
                this.dialog.add(ToppingsPopup, { 'title': 'Toppings', 'Topping_products': Topping_products, 'Globaltoppings': [] });
            }
        }
        super.clickLine(ev, orderline);

    },
    _setValue(val) {
        var self = this;
        const { numpadMode } = self.pos;
        const selectedLine = self.currentOrder.get_selected_orderline();
        if (selectedLine) {
            if (numpadMode === "quantity") {
                if (val === "remove") {
                    if (selectedLine.sh_topping_line_ids) {
                        for (let i = 0; i < selectedLine.sh_topping_line_ids.length; i++) {
                            const each_topping = selectedLine.sh_topping_line_ids[i];
                            if (each_topping && each_topping.id) {
                                self.currentOrder.removeOrderline(each_topping);
                            }
                        }
                    }
                }
                if (!selectedLine.sh_is_topping){
                    super._setValue(val)
                }
            }else{
                super._setValue(val)
            }
        }else{
            super._setValue(val)
        }
    }
});
