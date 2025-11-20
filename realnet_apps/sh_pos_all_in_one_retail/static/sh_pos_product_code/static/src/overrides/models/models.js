/** @odoo-module **/

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
  getDisplayData() {
    return {
        ...super.getDisplayData(),
        product_default_code_in_cart: !this.order_id.finalized && this.config.sh_enable_product_code_in_cart && this.config.sh_enable_prduct_code
                ? this.get_product().default_code
                : false,
        product_default_code_in_receipt: this.order_id.finalized &&
              this.config.sh_enable_product_code_in_receipt && this.config.sh_enable_prduct_code
                ? this.get_product().default_code
                : false
    };
},
});

patch(Orderline, {
  props: {
      ...Orderline.props,
      line: {
          ...Orderline.props.line,
          shape: {
              ...Orderline.props.line.shape,
              product_default_code_in_cart: { type: [Boolean, String, Number], optional: true },
              product_default_code_in_receipt: {type: [Boolean, String, Number], optional: true}
          },
      },
  },
});
