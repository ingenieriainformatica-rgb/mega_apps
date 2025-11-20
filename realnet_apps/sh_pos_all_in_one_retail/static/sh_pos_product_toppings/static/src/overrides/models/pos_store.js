/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { ToppingsPopup } from "@sh_pos_all_in_one_retail/static/sh_pos_product_toppings/app/Popups/ToppingsPopup/ToppingsPopup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        let self =  this;
        const line = await super.addLineToCurrentOrder(...arguments);
        if (self.config.sh_add_toppings_on_click_product && self.config.sh_enable_toppings && configure && line) {
            let Topping_products = []
            if(vals.product_id.pos_categ_ids && vals.product_id.pos_categ_ids.length > 0){
                for (let category of vals.product_id.pos_categ_ids) {
                    if (category && category.sh_product_topping_ids) {
                        Topping_products.push(...category.sh_product_topping_ids)
                    }
                }
            }
            if (vals.product_id && vals.product_id.sh_topping_ids && vals.product_id.sh_topping_ids.length > 0){
                for (let topping of vals.product_id.sh_topping_ids) {
                    if (!Topping_products.includes(topping)) {
                        Topping_products.push(topping);
                    }
                }
            }
            if (Topping_products.length > 0) {               
                await self.dialog.add(ToppingsPopup, { 'title': 'Toppings', 'Topping_products': Topping_products, 'Globaltoppings': [] });
            }
        }
       return line
    },
    async printChanges(order, orderChange) {
        const unsuccedPrints = [];
        const lastChangedLines = order.last_order_preparation_change.lines;
        orderChange.new.sort((a, b) => {
            const sequenceA = a.pos_categ_sequence;
            const sequenceB = b.pos_categ_sequence;
            if (sequenceA === 0 && sequenceB === 0) {
                return a.pos_categ_id - b.pos_categ_id;
            }

            return sequenceA - sequenceB;
        });

        for (const printer of this.unwatched.printers) {
            const changes = this._getPrintingCategoriesChanges(
                printer.config.product_categories_ids,
                orderChange
            );
            const toPrintArray = this.preparePrintingData(order, changes);
            const diningModeUpdate = orderChange.modeUpdate;
            if (diningModeUpdate || !Object.keys(lastChangedLines).length) {
                // Prepare orderlines based on the dining mode update
                const lines =
                    diningModeUpdate && Object.keys(lastChangedLines).length
                        ? lastChangedLines
                        : order.lines;

                // converting in format we need to show on xml
                const orderlines = Object.entries(lines).map(([key, value]) => ({
                    basic_name: diningModeUpdate ? value.basic_name : value.product_id.name,
                    isCombo: diningModeUpdate ? value.isCombo : value.combo_item_id?.id,
                    quantity: diningModeUpdate ? value.quantity : value.qty,
                    note: value.note,
                    attribute_value_ids: value.attribute_value_ids,
                    sh_is_topping : value.sh_is_topping,
                    display_name: diningModeUpdate ? value.basic_name : value.product_id.name,
                }));

                // Print detailed receipt
                const printed = await this.printReceipts(
                    order,
                    printer,
                    "New",
                    orderlines,
                    true,
                    diningModeUpdate
                );
                if (!printed) {
                    unsuccedPrints.push("Detailed Receipt");
                }
            } else {
                // Print all receipts related to line changes
                for (const [key, value] of Object.entries(toPrintArray)) {
                    const printed = await this.printReceipts(order, printer, key, value, false);
                    if (!printed) {
                        unsuccedPrints.push(key);
                    }
                }
                // Print Order Note if changed
                if (orderChange.generalNote) {
                    const printed = await this.printReceipts(order, printer, "Message", []);
                    if (!printed) {
                        unsuccedPrints.push("General Message");
                    }
                }
            }
        }

        // printing errors
        if (unsuccedPrints.length) {
            const failedReceipts = unsuccedPrints.join(", ");
            this.dialog.add(AlertDialog, {
                title: _t("Printing failed"),
                body: _t("Failed in printing %s changes of the order", failedReceipts),
            });
        }
    }
});
