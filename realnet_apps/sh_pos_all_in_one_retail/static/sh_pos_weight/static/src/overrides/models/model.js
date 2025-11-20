/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosOrder.prototype, {
    get_total_weight () {
    
        var order = this
        
        var total_weight = 0.0
        if (order.get_orderlines()) {
            for(let line of order.get_orderlines()){
                total_weight += line.product_id.weight * line.qty
            }
        }
        return total_weight
    },
    get_total_volume () {
        var order = this;
        var total_volume = 0.0
        if (order.get_orderlines()) {
            for(let line of order.get_orderlines()){
                total_volume += line.product_id.volume * line.qty
            }
        } 
        return total_volume
        
    },
    export_for_printing() {
        var orders = super.export_for_printing(...arguments);
        orders['total_product_weight'] = this.get_total_weight() || 0
        orders['total_product_volume'] = this.get_total_volume() || 0
        return orders
    }
});

patch(PosOrderline.prototype, {
    
    getDisplayData() {        
        return {
            ...super.getDisplayData(),

            weight_in_cart: this.order_id && !this.order_id.finalized && this.config.enable_weight,
            weight_in_receipt: this.order_id && this.order_id.finalized && this.config.product_weight_receipt,
            volume_in_receipt : this.order_id && this.order_id.finalized && this.config.product_volume_receipt,
            volume_in_cart: this.order_id && !this.order_id.finalized && this.config.enable_volume,

            product_weight: (this.product_id.weight * this.qty),
            product_volume: (this.product_id.volume * this.qty),
        };
    },
    
});
