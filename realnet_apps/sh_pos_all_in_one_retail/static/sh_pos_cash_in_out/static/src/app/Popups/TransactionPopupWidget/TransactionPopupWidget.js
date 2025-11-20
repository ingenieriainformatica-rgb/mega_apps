/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Component, useState, reactive } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Dialog } from "@web/core/dialog/dialog";


export class TransactionPopupWidget extends Component {
    static template = "sh_pos_all_in_one_retail.TransactionPopupWidget";
    static components = { Dialog };
    setup() {
        super.setup();
        this.pos = usePos();
    }
    confirm() {
        alert("confirm")
    }
}
