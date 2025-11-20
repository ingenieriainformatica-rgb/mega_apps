/** @odoo-module **/
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { patch } from "@web/core/utils/patch";

patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                product_weight: { type: Number, optional: true },
                product_volume: { type: Number, optional: true },
                weight_in_cart: { type: Boolean, optional: true },
                weight_in_receipt: { type: Boolean, optional: true },
                volume_in_receipt: { type: Boolean, optional: true },
                volume_in_cart: { type: Boolean, optional: true },
            },
        },
    },
});
