/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    get_pricelist_icon(){        
        return '/sh_pos_all_in_one_retail/static/sh_pos_line_pricelist/static/src/img/price_list.png';
    },
    getDisplayData() {
        return {
            ...super.getDisplayData(),
            pricelist_icon: this.order_id && !this.order_id.finalized ? this.get_pricelist_icon() : "" ,
        };
    },
});

patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                productId: {type: Number,optional: true,},
                pricelist_icon: {type: String,optional: true,},
            },
        },
    },
});
