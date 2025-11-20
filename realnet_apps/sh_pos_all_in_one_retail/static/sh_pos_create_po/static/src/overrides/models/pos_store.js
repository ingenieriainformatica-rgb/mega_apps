    /** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { ShPOConfirmPopup } from "@sh_pos_all_in_one_retail/static/sh_pos_create_po/app/Popups/sh_po_confirm_popup/sh_po_confirm_popup";

patch(PosStore.prototype,  {
    async setup() {
        await super.setup(...arguments)
        this.all_purchase_orders = []
    },
    get_all_orders: function () {
        return this.all_purchase_orders;
    },
    remove_all_purchase_orders: function () {
        this.all_purchase_orders = [];
    },
    async  create_purchase_order() {
        var self = this;

        var All_PO = self.get_all_orders();
        const serializedOrder = All_PO.map((order) => order.serialize({ orm: true }));
        
        return await self.data.call("pos.order", "sh_create_purchase", [serializedOrder, self.config.select_purchase_state]);
    }
    
});

