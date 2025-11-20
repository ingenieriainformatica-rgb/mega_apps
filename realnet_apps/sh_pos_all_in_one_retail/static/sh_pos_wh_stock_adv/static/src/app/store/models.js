/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PosOrder } from "@point_of_sale/app/models/pos_order";


patch(PosOrderline.prototype, {
    set_quantity(quantity, keep_price) {
        var self = this;
        let old_qty =  this.get_quantity()
        var res = super.set_quantity(...arguments)

        if (this && this.order_id && this.order_id.get_selected_orderline()) {
            if (quantity && this.config.sh_show_qty_location && this.config.sh_update_real_time_qty && this.config.sh_update_quantity_cart_change) {
                var dic = {
                    'product_id': this.get_product().id,
                    'location_id': self.config.sh_pos_location ? self.config.sh_pos_location.id : false,
                    'quantity': quantity,
                    "old_quantity" : old_qty,
                    'manual_update': true,

                }
                posmodel.env.services.orm.call("pos.config", "update_sh_stock", [self.config.id, dic]);

            }
            if (!quantity && this.config.sh_show_qty_location && this.config.sh_update_real_time_qty && this.config.sh_update_quantity_cart_change) {
                var vals = {
                    'product_id': this.get_product().id,
                    'location_id': self.config.sh_pos_location ? self.config.sh_pos_location.id : false,
                    'quantity': 0,
                    "old_quantity" : old_qty,
                    'manual_update': true,

                }
                posmodel.env.services.orm.call("pos.config", "update_sh_stock", [self.config.id, vals]);
            }
        }

        return res
    }
});

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        // this.onNotified("stock_update", (message) => {
        //     let self = this;
        //     if (message && (self.config.sh_update_real_time_qty || self.config.sh_update_quantity_cart_change)) {
        //         for (let i = 0; i < message.length; i++) {
        //             const data = message[i];
        //             let quant = self.models["stock.quant"].get(data.qaunt_id)
        //             if (quant) {
        //                 quant.sh_qty = data.quantity
        //             }
        //         }
        //     }
        // });

    },
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        const old_line = this.models["pos.order.line"].find((each_line) => (each_line.product_id && each_line.product_id.id == vals.product_id.id))
        let line =  await super.addLineToCurrentOrder(...arguments)
        var self = this
        if (self.config.sh_update_real_time_qty && self.config.sh_show_qty_location && !old_line ) {
            var dic = {
                'product_id': vals.product_id.id,
                'location_id': self.config.sh_pos_location ? self.config.sh_pos_location.id : false,
                'quantity': parseInt(line.qty),
                'manual_update': false
            }
            this.env.services.orm.call("pos.config", "update_sh_stock", [self.config.id,dic]);
        }
        return  line
    }
});
