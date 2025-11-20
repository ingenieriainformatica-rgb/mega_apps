/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, useState, reactive } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Dialog } from "@web/core/dialog/dialog";


export class LabelPopup extends Component {
    static template = "sh_pos_all_in_one_retail.LabelPopup";
    static components = { Dialog };
    setup() {
        super.setup();
        this.section = 'Section' || "";
        this.pos = usePos();
        this.state = useState({
            value: this.props.lable || ""
        });
    }
    close() {
        this.props.close();
    }
    confirm() {
        var self = this
        var value = this.state.value
        if (value) {
            var order = this.pos.get_order()
            var product = this.props.product
            if (order && product) {
                reactive(this.pos).addLineToCurrentOrder({ product_id: product, merge: false, "add_section": value }, {});
            }
            this.props.getPayload(this.state.value);
            this.props.close();
        } else {
            self.popup.add(ErrorPopup, {
                title: this._t('Label Not Found !'),
                body: this._t('Please Add Label')
            })
        }
    }
}
