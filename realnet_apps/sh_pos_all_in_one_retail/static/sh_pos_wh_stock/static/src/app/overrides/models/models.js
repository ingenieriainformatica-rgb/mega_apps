/** @odoo-module **/

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";


patch(PosOrderline.prototype, {
    getDisplayData() {
        return {
            ...super.getDisplayData(),
            product_type : this.get_product() ? this.get_product().type : false,
            productId :  this.get_product() ? this.get_product().id :false
        };
    }     
});
