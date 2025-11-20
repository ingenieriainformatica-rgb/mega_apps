/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments)
        this.all_sale_orders = []
    },
    get_all_sale_orders() {
        return this.all_sale_orders;
    },
    remove_all_sale_orders() {
        this.all_sale_orders = [];
    },
    async create_sale_order() {
        var self = this;
        var All_SO = self.get_all_sale_orders();
        const serializedOrder = All_SO.map((order) => order.serialize({ orm: true }));
        return await self.data.call("pos.order", "sh_create_sale_order", [serializedOrder, self.config.select_order_state]);
    }

});
