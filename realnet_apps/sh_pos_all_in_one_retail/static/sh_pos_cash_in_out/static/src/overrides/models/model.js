/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async setup(){
        await super.setup(...arguments)
        this.data.connectWebSocket("CASH_IN_OUT_CREATE", async (data) => {
            if(this.config  &&  this.config.sh_enable_cash_in_out_statement){
                await this.data.read("sh.cash.in.out", [data.data]);
            }
        });
    },
});
