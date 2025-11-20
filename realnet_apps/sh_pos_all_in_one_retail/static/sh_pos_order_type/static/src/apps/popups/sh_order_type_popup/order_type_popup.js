/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class SelectionOrderTypePopup extends Component {
    static template = "sh_pos_all_in_one_retail.SelectionOrderTypePopup";
    static components = { Dialog };
    setup() {
        this.state = useState({ selectedId: this.props.list.find((item) => item.isSelected) });
    }
    selectItem(itemId) {
        this.state.selectedId = itemId;
        this.confirm();
    }
    typeImage(id) {
        return `/web/image/sh.order.type/${id}/img`;
    }
    computePayload() {
        const selected = this.props.list.find((item) => this.state.selectedId === item.id);
        return selected && selected.item;
    }
    confirm() {
        this.props.getPayload(this.computePayload());
        this.props.close();
    }
}
