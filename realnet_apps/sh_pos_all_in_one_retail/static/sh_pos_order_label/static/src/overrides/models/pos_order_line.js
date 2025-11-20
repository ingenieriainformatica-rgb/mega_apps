/** @odoo-module **/

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";

patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                label_in_receipt: { type: Boolean, optional: true },
                add_section: { type: String, optional: true },

            },
        },
    },
});

patch(PosOrderline.prototype, {
    setup(vals) {
        super.setup(...arguments)
        this.add_section = this.add_section || ""
    },
    set_orderline_label(value) {
        this.add_section = value
    },
    get_orderline_label() {
        return this.add_section
    },
    can_be_merged_with(orderline) {
        return (
            this.add_section === "" &&
            super.can_be_merged_with(...arguments)
        );
    },
    getDisplayData() {
        var self = this;
        return {
            ...super.getDisplayData(),
            label_in_receipt: self.config.enable_order_line_label && self.config.enable_order_line_label_in_receipt,
            add_section: self.add_section
        };
    },
})
