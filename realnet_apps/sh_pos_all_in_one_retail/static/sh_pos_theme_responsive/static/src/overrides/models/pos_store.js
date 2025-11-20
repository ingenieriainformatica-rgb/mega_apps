/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(PosStore.prototype, {
    //@override
    
    async setup() {
        await super.setup(...arguments);
        // this.pos = usePos();
        if(this && this.models && this.models['sh.pos.theme.settings'] && this.models['sh.pos.theme.settings'].getAll() && this.models['sh.pos.theme.settings'].getAll()[0] && this.models['sh.pos.theme.settings'].getAll()[0].sh_mobile_start_screen == "cart_screen") {
            this.mobile_pane = "left";
        }
    },
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        var res = await super.addLineToCurrentOrder(vals, opts, configure)
        let self = this
        if(this.models['sh.pos.theme.settings'] && this.models['sh.pos.theme.settings'].getAll()[0] && this.models['sh.pos.theme.settings'].getAll()[0].display_product_cart_qty){
            let orderlines = Object.values(this.get_order().get_orderlines())
            
            let other_line_with_same_product = orderlines.filter((x) => (x.product_id.id == self.get_order().get_selected_orderline().product_id.id))
            
            if (other_line_with_same_product.length > 0) {
                let total_qty = 0
                // other_line_with_same_product.map((x) => total_qty += x.qty)
                total_qty += self.get_order().get_selected_orderline().qty
                if (self.get_order().product_with_qty) {
                    self.get_order().product_with_qty[self.get_order().get_selected_orderline().product_id.id] = total_qty != 0 ? total_qty : false;
                } else {
                    self.get_order().product_with_qty = {}
                    self.get_order().product_with_qty[self.get_order().get_selected_orderline().product_id.id] = total_qty != 0 ? total_qty : false;
                }
                self.get_order()['product_with_qty']
            } else {
                if (self.get_order().product_with_qty) {
                    self.get_order().product_with_qty[self.get_order().get_selected_orderline().product_id.id] = self.get_order().get_selected_orderline().qty != 0 ? self.get_order().get_selected_orderline().qty : false
                } else {
                    self.get_order().product_with_qty = {};
                    self.get_order().product_with_qty[self.get_order().get_selected_orderline().product_id.id] = self.get_order().get_selected_orderline().qty != 0 ? self.get_order().get_selected_orderline().qty : false
                }
            }
        }
        return res
    }
    // get cart_item_count(){
    //     // return 2
    //     alert()
    //     if(this.pos_theme_settings_data && this.pos_theme_settings_data[0].display_cart_order_item_count && this.get_order()){
    //         return this.get_order().get_orderlines().length
    //     }else{
    //         return 0
    //     }
    // }
});