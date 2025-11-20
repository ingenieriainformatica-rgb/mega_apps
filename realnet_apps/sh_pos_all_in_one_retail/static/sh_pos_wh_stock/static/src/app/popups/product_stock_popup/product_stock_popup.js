/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";


export class ProductQtyPopup extends Component {
    static template = "sh_pos_all_in_one_retail.ProductQtyPopup";
    static components = {  Dialog };

    setup() {
        super.setup();
        this.pos = usePos();

    }
    get getStock() {
        return this.props.product_stock
    }
    close() {
        this.props.close();
    }
}
