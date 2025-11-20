/** @odoo-module */

import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(Orderline.prototype, {
    setup() {
        super.setup()
        this.pos = usePos();
        this.popup = useService("dialog");
    },
    async _clickRemoveLine(line_id) {
        let line = this.pos.models["pos.order.line"].getBy("id" , line_id)
        this.pos.get_order().removeOrderline(line)
    }
});
