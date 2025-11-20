/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        if (this.pos.config.sh_show_qty_location) {
            var order = this.currentOrder;
            var lines = order.get_orderlines()
            if (lines && lines.length) {
                for (let line of lines) {
                    let stock_list  = this.pos.models["stock.quant"].getAll().filter((quant) => {
                        if (quant.product_id && quant.product_id.id == line.get_product().id && quant.location_id && quant.location_id.usage == 'internal'  && quant.location_id.id == this.pos.config.sh_pos_location.id) { return true } else { return false }
                    })                    
                    if(stock_list){
                        if (stock_list && stock_list.length) {
                            stock_list[0]['quantity'] -= line.qty
                        }
                    }
                }
            }
        }
        await super.validateOrder(...arguments);
    },
});
