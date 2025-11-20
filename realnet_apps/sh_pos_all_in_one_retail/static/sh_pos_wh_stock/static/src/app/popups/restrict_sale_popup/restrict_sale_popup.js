/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";


export class ProductStockRestrict extends Component {
    static template = "sh_pos_all_in_one_retail.ProductStockRestrict";
    static components = {  Dialog };

    setup() {
        super.setup();
        this.pos = usePos();
    }
    confirm() {
        this.props.confirm();
        this.props.close();
    }
    close() {
        this.props.close();
        return false
    }
    get imageUrl() {
        const product = this.props.product;
        return `/web/image?model=product.product&field=image_128&id=${product.id}&unique=${product.write_date}`;
    }
}
