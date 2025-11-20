/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { formatFloat } from "@web/core/utils/numbers";


patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
    },
    set_order_global_discount(discount) {
        this.order_global_discount = discount;
    },
    get_order_global_discount() {
        return this.order_global_discount || false;
    },
    export_as_JSON() {
        var self = this;
        var orders = super.export_as_JSON(...arguments);
        orders['sh_global_discount'] = self.order_global_discount || false
        return orders
    },
    export_for_printing() {
        var self = this;
        var orders = super.export_for_printing(...arguments);
        orders['sh_global_discount'] = self.order_global_discount || false
        return orders
    },
    init_from_JSON (json) {
        super.init_from_JSON(...arguments);
        if (json && json.sh_global_discount){
            this.order_global_discount = json.sh_global_discount || ""
        }
    },
});

patch(PosOrderline.prototype, {
    setup() {
        super.setup(...arguments);
        this.global_discount;
        this.fix_discount;
        this.total_discount;

        if (this && this.order_id && this.order_id.get_orderlines().length == 0) {
            this.order_id.set_order_global_discount(0.0);
        }
    },
    getDisplayData() {
        let res = super.getDisplayData()
        if(res.discount){
            let int_discount =  parseFloat(res.discount).toFixed(2)
            res["discount"] = int_discount
        }
        return res
    },
    set_global_discount(global_discount) {
        this.global_discount = global_discount;
    },
    get_global_discount() {
        return this.global_discount;
    },
    set_fix_discount(discount) {
        this.fix_discount = discount;
    },
    get_fix_discount() {
        return this.fix_discount;
    },
    get_sh_discount_str() {
        return this.discount.toFixed(2);
    },
    set_total_discount(discount) {
        this.total_discount = discount;
    },
    get_total_discount() {
        return this.total_discount || false;
    },
    set_custom_discount(discount) {
        var disc = Math.min(Math.max(discount || 0, 0), 100);
        this.discount = disc;
        this.discountStr = "" + formatFloat(disc, { digits: [69, 2] });
    },
});
