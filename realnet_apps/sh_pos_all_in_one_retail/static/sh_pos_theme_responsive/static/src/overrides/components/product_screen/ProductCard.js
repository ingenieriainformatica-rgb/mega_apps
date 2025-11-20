/** @odoo-module */

import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";

patch(ProductCard.prototype, {
    setup() {
        super.setup()
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        onMounted(this.onMounted);
    },
    onMounted() {
        if(this.ui.isSmall){
            this.pos.isMobile = true
            if(document.getElementsByClassName('sh_product_list_view').length > 0 && document.getElementsByClassName('sh_product_list_view')[0]){
                document.getElementsByClassName('sh_product_list_view')[0].classList.add('hide_sh_product_list_view')
            }
            if(document.getElementsByClassName('product-list').length > 0 && document.getElementsByClassName('product-list')[1]){
                document.getElementsByClassName('product-list')[1].classList.remove('hide_product_list_container')
            }
        }
    }
});
