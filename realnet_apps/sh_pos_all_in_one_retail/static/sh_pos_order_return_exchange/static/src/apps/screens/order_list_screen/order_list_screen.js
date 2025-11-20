/** @odoo-module **/

import { OrderListScreen } from "@sh_pos_all_in_one_retail/static/sh_pos_order_list/apps/screen/order_list_screen/order_list_screen";
import { ReturnOrderPopup } from "@sh_pos_all_in_one_retail/static/sh_pos_order_return_exchange/apps/popups/return_order_popup/return_order_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";


patch(OrderListScreen.prototype, {
    setup() {
        this.is_return_filter = false;
        super.setup()
        this.dialog = useService("dialog");
    },
    get_return_filter() {
        return this.is_return_filter;
    },
    apply_return_filter(data) {
        this.is_return_filter = data
    },
    // async sh_return_pos_order(ev) {
    //     $(ev.target).toggleClass('highlight')
    //     this.apply_return_filter(!this.get_return_filter());
    //     this.offset = 0;
    //     this.fetch()
    // },
    get allPosOrders() {
        if (this.isSearch) {
            var orders = this.subFilterdOrders;
            return orders.sort((function (a, b) { return b[0]['id'] - a[0]['id'] }))
        } else {
            // retunr order fileter
            if (this.get_return_filter()) {
                var orders = Object.values(this.pos.db.pos_order_by_id)
                var filterd_orders = orders.filter((x) => x[0].is_return_order) || []
                if (filterd_orders && filterd_orders.length) {
                    return filterd_orders.sort((function (a, b) { return b[0]['id'] - a[0]['id'] }))
                } else {
                    return []
                }
            } else {
                var orders = Object.values(this.pos.db.pos_order_by_id)
                var filterd_orders = orders.filter((x) => !x[0].is_return_order) || []
                if (filterd_orders && filterd_orders.length) {
                    return filterd_orders.sort((function (a, b) { return b[0]['id'] - a[0]['id'] }))
                } else {
                    return orders
                }
            }
        }
    },
    async exchange_pos_order(order) {
        var self = this;
        event.stopPropagation();
        console.log('order -> ', order);

        await makeAwaitable(this.dialog, ReturnOrderPopup, {
            title: _t("Exchange"),
            'order': order,
            'lines': order.lines,
            'sh_return_order': false,
            'exchange_order': true,
        });


    },
    async return_pos_order(order) {
        var self = this;
        event.stopPropagation();
        console.log('ORder', order);
        await makeAwaitable(this.dialog, ReturnOrderPopup, {
            title: _t("Return"),
            'order': order,
            'lines': order.lines,
            'sh_return_order': true,
            'exchange_order': false,
        })

    }
})