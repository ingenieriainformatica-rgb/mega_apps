/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { useState } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup(){
        super.setup(...arguments)
        this.state = useState({
            general_note : this.pos.get_order().general_note ? this.pos.get_order().general_note : "",
        });
    },
    async validateOrder(isForceValidate) {        
        if (this.state.general_note) {
            this.pos.get_order().general_note = this.state.general_note;
        }
        return await super.validateOrder(...arguments);
    },
    
});
