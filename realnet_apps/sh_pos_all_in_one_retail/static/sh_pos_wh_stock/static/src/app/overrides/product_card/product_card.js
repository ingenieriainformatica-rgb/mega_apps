/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";


patch(ProductCard.prototype, {
    setup(){
        super.setup()
        this.pos = usePos();
    },
    get get_display_stock() {
        var self = this;
        var product_id = this.props.productId
        let qty = 0.0
        const stocks = this.pos.models["stock.quant"].find((quant) => (quant.product_id && quant.product_id.id == product_id) && quant.location_id.id == self.pos.config.sh_pos_location.id)
        if(stocks){
            qty = stocks.quantity - stocks.sh_qty
        }
        return qty
    },
    get_length_of_varients(){
        return this.props.product.attribute_line_ids.map((a) => a.product_template_value_ids).flat().length < 1;
    }
})
