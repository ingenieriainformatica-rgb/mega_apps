/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(OrderWidget.prototype, {
    setup(){
        super.setup(...arguments);
        this.props["global_discount"] = 0.0
        this.pos = usePos();
    },
    pos_discount() {
        var order = this.pos.get_order();
        return order.get_order_global_discount()
          ? parseFloat(order.get_order_global_discount()).toFixed(2)
          : 0;
    },
});
