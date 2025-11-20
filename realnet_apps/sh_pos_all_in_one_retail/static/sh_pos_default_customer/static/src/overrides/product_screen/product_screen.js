/** @odoo-module **/

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        var self = this;
        var order = self.pos.get_order();
        console.log("order", order , order.get_partner());
        
        if (order && !order.get_partner()) {
            if (self.pos.config.sh_enable_default_customer && self.pos.config.sh_default_customer_id) {
                var set_partner = self.pos.config.sh_default_customer_id;
                if (set_partner) {
                    order.set_partner(set_partner);
                }
            } else if (self.pos && self.pos.get_order()) {
                self.pos.get_order().set_partner(false);
            }
        }
    },
});
