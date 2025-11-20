/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
//  UOM feature code

patch(PosOrderline.prototype, {
    getDisplayData() {
        let result = super.getDisplayData()
        console.log("this.get_custom_uom()", this.get_custom_uom());
        if(this.get_custom_uom()){
            result["unit"] = this.get_custom_uom().name
        }
        return result
    },
    set_custom_uom(uom_name){
        if(uom_name.uom_id){
            this.update({ sh_uom_id: uom_name.uom_id });
        }else{
            this.update({ sh_uom_id: uom_name });

        }
    },
    get_custom_uom(){
        return this.sh_uom_id
    }
});


patch(PosStore.prototype, {
    get linesToRefund() {
        let res = super.linesToRefund
        console.log("res ", res);
        
        return res 
    }
})