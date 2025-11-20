/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    get_product_image_url(product_id,write_date){        
        return `/web/image?model=product.product&field=image_128&id=${product_id}&write_date=${write_date}&unique=1`;
    },
    getDisplayData() {
        return {
            ...super.getDisplayData(),
            product_img: this.order_id && !this.order_id.finalized ? this.get_product_image_url(this.product_id.id,this.write_date) : "" ,
            show_custom_line: this.order_id && !this.order_id.finalized ? true : false,
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
                product_img: { type: String, optional: true },
                show_custom_line: { type: Boolean, optional: true },
            },
        },
    },
});
