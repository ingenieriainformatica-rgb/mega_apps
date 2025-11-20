/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
  get productsToDisplay() {
    var products = super.productsToDisplay;
    var product_list = [];
    if (this.pos.config.sh_enable_own_product) {
      if(this.pos.get_cashier()){
        if (this.pos.get_cashier()._role != "manager") {
          for (var i = 0; i < products.length; i++) {
            if (products[i].sh_select_user.length != 0) {
              product_list.push(products[i]);
            }
          }
        } else {
          return products;
        }
      }else {
        return products;
      }
      if (product_list.length > 0) {
        return product_list;
      } else {
        return [];
      }
    } else {
      return products;
    }
  },
});
