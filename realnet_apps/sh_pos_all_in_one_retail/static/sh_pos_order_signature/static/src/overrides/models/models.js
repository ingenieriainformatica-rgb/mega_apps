/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    set_signature_date(signature_date) {
        this.signature_date = signature_date  
    },
    get_signature_date() {
        return this.signature_date || false;
    },
    set_signature_name(signature_name) {
        this.signature_name = signature_name  
    },
    get_signature_name() {
        return this.signature_name || false;
    },
    set_signature(signature) {
        this.signature = signature  
    },
    get_signature() {
        return this.signature || false;
    },
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        result.signature= this.get_signature()
        result.signature_name= this.get_signature_name()
        result.signature_date= this.get_signature_date()
        return result;
    
    },
});
