/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { omit } from "@web/core/utils/objects";



patch(PosOrderline.prototype, {
    get_customer_note() {
        if(this.config.enable_orderline_note && this.customer_note ){
            const notes = (this.customer_note ? this.customer_note.split('\n') : []).filter(note => note.trim() !== ', ' && note.trim() !== '');
              const result = notes.join(' , ');
              return result
        }else{
            super.get_customer_note()
        }
    }
    
});



patch(PosOrder.prototype, {
    export_as_JSON () {
        const json = super.export_as_JSON(...arguments);
        json.order_note = this.get_global_note() || null;
        return json;
    },
    export_for_printing(baseUrl, headerData) {
        const baseData = super.export_for_printing(baseUrl, headerData);
        const orderlines = this.getSortedOrderlines().map((l) => {
            const displayData = l.getDisplayData();
            if (this.config.display_orderline_note_receipt) {
                return displayData;
            } else {
                return omit(displayData, "internalNote"); 
            }
        });
        return {
            ...baseData,
            orderlines, 
        };

    }
})