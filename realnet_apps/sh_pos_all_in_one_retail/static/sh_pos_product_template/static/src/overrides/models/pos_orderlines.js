/** @odoo-module **/

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    setup(vals) {
        super.setup(...arguments)
        this.is_template_product = this.is_template_product || false
    },
    set_template_product(value) {
        this.is_template_product = value
    },
    get_is_template_product() {
        return this.is_template_product
    }, 
})
