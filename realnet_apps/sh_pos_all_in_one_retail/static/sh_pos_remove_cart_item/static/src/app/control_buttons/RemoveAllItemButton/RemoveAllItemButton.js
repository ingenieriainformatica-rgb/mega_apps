/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { usePos } from "@point_of_sale/app/store/pos_hook";


patch(ControlButtons.prototype, {
    async onClickRemoveItem() {
        var self = this;
        const order = this.pos.get_order()
        if (order && order.get_orderlines() && order.get_orderlines().length > 0) {
            var orderlines = order.get_orderlines();
            if (self.pos.config.sh_remove_all_item && self.pos.config.sh_validation_to_remove_all_item) {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Delete Items"),
                    body: _t(
                        'Do you want remove all items?'
                    ),
                    confirm: () => {
                        [...orderlines].map(async (line) => await self.pos.get_order().removeOrderline(line))
                    },
                    cancel: () => { },
                });
            }
            else {
                [...orderlines].map(async (line) => await self.pos.get_order().removeOrderline(line))
            }
        }
    }

})
