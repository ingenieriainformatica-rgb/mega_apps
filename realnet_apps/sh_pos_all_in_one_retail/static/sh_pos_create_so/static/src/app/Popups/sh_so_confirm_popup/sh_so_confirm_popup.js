/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class ShSOConfirmPopup extends Component {
    static template = "sh_pos_all_in_one_retail.ShSOConfirmPopup";
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
        this.pos.remove_all_sale_orders()
        return res
    }
}
