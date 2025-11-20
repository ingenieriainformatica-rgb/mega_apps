/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        if ( this.pos.config.sh_update_real_time_qty ){ 
            // don't have to change qty from here
            console.log('Stock Update');
        }else{
            if (this.pos.config.sh_show_qty_location) {
                var order = this.currentOrder;
                var lines = order.get_orderlines()
                var location_id = this.pos.config.sh_pos_location ? this.pos.config.sh_pos_location[0] : false
                if (lines && lines.length) {
                    for (let line of lines) {
                        let stock_list = this.pos.db.get_stock_by_product_id(line.get_product().id)
                        var sh_stock = stock_list.filter((stock) => stock.location_id == location_id)
                        if (sh_stock && sh_stock.length) {
                            sh_stock[0]['quantity'] -= line.quantity
                        }
                    }
                }
            }
        }
        await super.validateOrder(...arguments);
    },
});
