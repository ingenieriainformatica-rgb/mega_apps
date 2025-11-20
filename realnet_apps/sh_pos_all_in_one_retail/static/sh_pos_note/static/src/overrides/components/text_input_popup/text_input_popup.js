/** @odoo-module */

import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useState } from "@odoo/owl";

patch(TextInputPopup.prototype, {
    setup() {
        super.setup()
        this.pos = usePos();
        this.value = useState({ "store_checkbox": false });
    },
    confirm() {
        super.confirm()
        if (this.value.store_checkbox) {
            let new_note = this.state.inputValue
             this.pos.models["pos.note"].create({"name" : new_note})
             this.pos.data.create("pos.note", [{ 'name': new_note }]);
        }
    }
});

patch(TextInputPopup, {
    props: {
        ...TextInputPopup.props,
        is_create: { type: Boolean, optional: true },
    },
});