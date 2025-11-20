/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Order, Orderline } from "@point_of_sale/app/store/models";

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        this.l10n_fr_hash = this.l10n_fr_hash || false;
        this.save_to_db();
    },
    get_orderline_by_id(id) {
        var result = []
        for (let line of this.get_orderlines()) {
            if (line.id == id) {
                result.push(line)
            }
        }
        return result
    },
    async set_orderline_options(orderline, options) {
        for (let all_orderline of this.get_orderlines()) {
            if (all_orderline.add_section) {
                orderline.set_ref_label(all_orderline.add_section)
            }

        }
        super.set_orderline_options(orderline, options);
    }
});

patch(Orderline.prototype, {
    set_ref_label(value) {
        this.ref_label = value
    },
    get_ref_label() {
        return this.ref_label
    },
});
