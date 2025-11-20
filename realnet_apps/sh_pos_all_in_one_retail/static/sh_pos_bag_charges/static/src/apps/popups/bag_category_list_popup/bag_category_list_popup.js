/** @odoo-module */

import { Component, reactive, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { Dialog } from "@web/core/dialog/dialog";



export class BagCategory_list_popup extends Component {
    static template = "sh_pos_bag_charges.BagCategory_list_popup";
    static components = {Dialog,ProductCard};

   
        setup() {
            this.pos = usePos();
           
        }
        async addProductToOrder(product) {
            await reactive(this.pos).addLineToCurrentOrder({ product_id: product }, {});
        }   
 
}



