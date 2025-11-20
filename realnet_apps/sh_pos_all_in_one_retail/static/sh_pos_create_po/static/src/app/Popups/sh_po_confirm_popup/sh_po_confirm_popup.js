/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";

export class ShPOConfirmPopup extends Component {
    static template = "sh_pos_all_in_one_retail.ShPOConfirmPopup";
    static components = {  Dialog };

    setup(){
        super.setup()
        this.pos = usePos();
    }
    confirm() {
        this.props.close();
        var self = this;
        var orderlines = self.pos.get_order().get_orderlines()
        let res = [...orderlines].map(async(line)=>await self.pos.get_order().removeOrderline(line))
        this.pos.remove_all_purchase_orders()
        return res
    }
}
