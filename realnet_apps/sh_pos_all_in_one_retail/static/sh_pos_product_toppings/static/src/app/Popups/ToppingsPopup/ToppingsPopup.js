/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class ToppingsPopup extends Component {
    static template = "sh_pos_product_toppings.ToppingsPopup";
    static components = { Dialog, ProductCard };

    setup() {
        super.setup();
        this.pos = usePos();
        this.dialog = useService("dialog");
    }
    close() {
        this.props.close()
    }
    get globalToppings() {
        return this.props.Globaltoppings
    }
    get toppingProducts() {
        return this.props.Topping_products
    }
    async addProductToOrder(product) {
        if (!this.pos.get_order()) {
            this.pos.add_new_order();
        }
        if (this.pos.config.sh_enable_toppings && this.pos.get_order() && this.pos.get_order().get_selected_orderline()) {
            let selected_line = this.pos.get_order().get_selected_orderline()
            await this.pos.addLineToCurrentOrder({
                product_id: product,
                sh_base_line_id: selected_line ? selected_line : false,
                sh_is_topping : true,
            }, {}, false);
            selected_line.set_has_topping(true)
            this.pos.get_order().select_orderline(selected_line);
        } else {
            await this.dialog.add(AlertDialog, { body: _t('Please Select Orderline !'), });
        }

    }
    getProductPrice(product) {
        return this.pos.getProductPriceFormatted(product);
    }
}
