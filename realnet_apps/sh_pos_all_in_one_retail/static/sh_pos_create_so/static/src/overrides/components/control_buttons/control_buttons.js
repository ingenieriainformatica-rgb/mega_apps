/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ShSOConfirmPopup } from "@sh_pos_all_in_one_retail/static/sh_pos_create_so/app/Popups/sh_so_confirm_popup/sh_so_confirm_popup";


patch(ControlButtons.prototype, {
    async createSo() {
        var self = this;
        var order = this.pos.get_order()
        var orderlines = order.get_orderlines()
        var client = order.get_partner();
        if (client != null) {
            if (orderlines.length != 0) {
                try {
                    self.pos.all_sale_orders.push(order)
                    var Orders = await this.pos.create_sale_order()
                    if (Orders && Orders.length > 0) { 
                        self.dialog.add(ShSOConfirmPopup, {
                            title: 'Sale Order Reference',
                            body: " Sale Order Created.",
                            SaleOrderId: Orders[0].id,
                            SaleOrderName: Orders[0].name
                        })
                    }

                } catch (error) {
                    throw error
                }
            }
            else {
                this.dialog.add(AlertDialog, {
                    title: 'Product is not available !',
                    body: 'Please Add Product In Cart !',
                });
            }
        }
        else {
            this.dialog.add(AlertDialog, {
                title: 'Partner is not available !',
                body: 'Please Select Partner!',
            });
        }
    },
});
