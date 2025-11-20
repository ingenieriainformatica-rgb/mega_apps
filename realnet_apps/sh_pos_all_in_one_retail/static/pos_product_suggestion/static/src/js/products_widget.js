/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { Component, reactive } from "@odoo/owl";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductInfoPopup } from "@point_of_sale/app/screens/product_screen/product_info_popup/product_info_popup";

class SuggestedProductList extends Component {
  static components = { ProductCard };
  static template = "sh_pos_all_in_one_retail.SuggestedProductList";
  setup() {
    this.pos = usePos()
    this.dialog = useService("dialog");

  }
  getProductName(product) {
    const productTmplValIds = product.attribute_line_ids
      .map((l) => l.product_template_value_ids)
      .flat();
    return productTmplValIds.length > 1 ? product.name : product.display_name;
  }
  async onProductInfoClick(product) {
    const info = await reactive(this.pos).getProductInfo(product, 1);
    this.dialog.add(ProductInfoPopup, { info: info, product: product });
  }
  async addProductToOrder(product) {
    await reactive(this.pos).addLineToCurrentOrder({ product_id: product }, {});
  }
  getProductPrice(product) {
    return this.pos.getProductPriceFormatted(product);
  }
  getProductImage(product) {
    return product.getImageUrl();
  }
}

registry.category("pos_screens").add("SuggestedProductList", SuggestedProductList);


patch(ProductScreen, {
  components: {
    ...ProductScreen.components,
    SuggestedProductList
  }
})

patch(ProductScreen.prototype, {
  setup() {
    super.setup(...arguments);
    this.final_suggest_products = [];
  },
  get_final_suggested_product_ids(products) {
    const self = this;
    const temp_suggest_ids = new Set(); // Use a Set to store unique IDs
    const final_suggest_products = [];

    for (const product of products) {

      if (product.suggestion_line.length > 0) {

        for (const sug_line of product.suggestion_line) {
          temp_suggest_ids.add(sug_line); // Add to the Set
        }
      }
    }

    if (temp_suggest_ids.size > 0) {
      for (const id of temp_suggest_ids) {
        final_suggest_products.push(id.product_suggestion_id)
      }
    }

    return final_suggest_products;
  },
  get suggestedproduct() {
    if (this.searchWord !== "") {
      const products = this.productsToDisplay
      const suggest = this.get_final_suggested_product_ids(products)

      return suggest;
    } else {
      return [];
    }
  },
});

