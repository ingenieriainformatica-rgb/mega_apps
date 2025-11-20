/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ToppingsPopup } from "@sh_pos_all_in_one_retail/static/sh_pos_product_toppings/app/Popups/ToppingsPopup/ToppingsPopup";


patch(ControlButtons.prototype, {
    async onClick() {
        let Globaltoppings = this.pos.models["product.product"].filter((product) => {
            return product.sh_is_global_topping;
        });
        
        if (Globaltoppings.length > 0) {
            await this.dialog.add(ToppingsPopup, { 'title': 'Global Topping', 'Topping_products': [], 'Globaltoppings': Globaltoppings });
        } else {
            await this.dialog.add(AlertDialog, { title: 'No Toppings', body: 'Not Found any Global Topping' });
        }
    }
    
});
