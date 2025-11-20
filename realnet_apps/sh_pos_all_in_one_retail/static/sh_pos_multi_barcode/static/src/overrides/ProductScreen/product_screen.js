/** @odoo-module */

import { patch } from '@web/core/utils/patch';
import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
     async _getProductByBarcode(code) {
        var product = await super._getProductByBarcode(code)
        if (!product && this.pos.config.sh_enable_multi_barcode){
            const records = await this.pos.data.searchRead("product.template.barcode",[["name", "ilike", code.base_code]]
            );
            if (records && records.length){
                product = records[0].product_id
            }
        }
        
        return product
    }
})
patch(ProductProduct.prototype, {
    get searchString() {
        var string = super.searchString
        if (this.barcode_line_ids && this.barcode_line_ids.length && posmodel.config.sh_enable_multi_barcode){
            for (let each_barcode of this.barcode_line_ids) {
                string += " "+each_barcode.display_name
            }
        }
        
        return string
    },
   
});
