/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status"
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreenStatus.prototype, {
    click(event){
        var self =  this;
        var order = this.props.order;
        let rounding = event.target.checked
        if (rounding == true) {
            order.set_is_payment_round(true);
            document.querySelector(".total").textContent= this.env.utils.formatCurrency(order.get_round_total_with_tax());
        } else {
            order.set_is_payment_round(false);
            document.querySelector(".total").textContent = this.env.utils.formatCurrency(order.get_total_with_tax());
        }
    }
})


patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        var self = this;
        if(this.pos.config.sh_enable_rounding ){
            if (this.currentOrder.get_is_payment_round()) {
                var rounding_price = this.currentOrder.total_rounding;
                this.currentOrder.set_validate_oreder(true)
                this.currentOrder.set_rounding_price(rounding_price);
                var round_product = this.pos.models["product.product"].find((product) => product ==  self.pos.config.round_product_id)  
                if(round_product){
                    
                    this.pos.addLineToCurrentOrder({
                        product_id: round_product,
                        qty: 1,
                        price_unit: rounding_price,
                    }, {}, false);
                }
            }else{
                this.currentOrder.set_rounding_price(0);
            }
            
            // remove pending payments before finalizing the validation
            for (let line of this.paymentLines) {
                if (!line.is_done()) this.currentOrder.remove_paymentline(line);
            }
        }
        await super.validateOrder(...arguments);
    }
})