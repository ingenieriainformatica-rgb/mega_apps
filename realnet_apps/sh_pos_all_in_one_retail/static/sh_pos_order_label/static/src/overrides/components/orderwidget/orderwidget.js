/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";

patch(OrderSummary.prototype, {
    remove_label(line) {
        if (this.pos.config.enabel_delete_label_with_product) {
            const orderlines = this.currentOrder.get_orderlines()
            const uuid = line.uuid
            var get_lable = false;
            const lines = orderlines.filter((line) => {
                if (line.uuid == uuid || get_lable) {
                    get_lable = true
                    if (line.uuid !== uuid && line.add_section !== "") {
                        get_lable = false
                        return false
                    } else {
                        return true
                    }
                } else {

                    return false
                }
            })

            for (let sh_line of lines) {
                this.currentOrder.removeOrderline(sh_line);
            }
        } else {
            this.currentOrder.removeOrderline(line);
        }

    }
})
