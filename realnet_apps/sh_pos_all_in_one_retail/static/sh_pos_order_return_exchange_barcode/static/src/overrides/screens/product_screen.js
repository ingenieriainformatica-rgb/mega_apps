/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { ReturnOrderPopup } from "@sh_pos_all_in_one_retail/static/sh_pos_order_return_exchange/apps/popups/return_order_popup/return_order_popup";
import { useService } from "@web/core/utils/hooks";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";


patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments)
        this.dialog = useService("dialog");
    },
    async _barcodeProductAction(code) {
        var self = this;
        var scaned_code = code.base_code;
        var pos_orders = this.pos.models["pos.order"].getAll();

        let barcode_order = pos_orders.filter(order => {
            return order.pos_reference == scaned_code;
        });

        if (barcode_order && barcode_order[0]) {
            await makeAwaitable(this.dialog, ReturnOrderPopup, {
                title: _t("Return"),
                'order': barcode_order[0],
                'lines': barcode_order[0].lines,
                'sh_return_order': true,
                'exchange_order': true,
                'from_barcode': true,
            });

            // return product;

        }
        else {
            await super._barcodeProductAction(...arguments)
        }
    },

})