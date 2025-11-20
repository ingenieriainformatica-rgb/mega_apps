/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    export_for_printing() {
        var orders = super.export_for_printing(...arguments);
        orders['total_items'] = this.get_orderlines().length || false      
        orders['total_qty'] = this.get_total_qty() || false  
        return orders
    },
    get_total_qty() {
        let qty = 0 
        for(let line of this.get_orderlines()){
            qty += line.get_quantity()
        }
        return qty
    }
});
