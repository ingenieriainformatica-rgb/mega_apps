/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(vals)
        this.sh_order_type_id = this.get_order_type() || (this.config_id && this.config_id.order_type_id)
    },
    set_order_type(type){
        this.sh_order_type_id = type 
        
    },
    get_order_type(){
        return this.sh_order_type_id
    },
    export_for_printing(baseUrl, headerData) {
        var res = super.export_for_printing(...arguments)
        if (this && this.config_id && this.config_id.enable_order_type && this.config.order_type_id){
            res.headerData["current_order_type"] = this.get_order_type().name
        }
        return res
    },
});
