/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { ShortcutTipsPopup } from "@sh_pos_all_in_one_retail/static/sh_pos_keyboard_shortcut/app/popups/shortcut_tips_popup/shortcut_tips_popup";


patch(ControlButtons.prototype, {
    async onClick() {
        await  this.dialog.add(ShortcutTipsPopup,{
            title : "Shortcut Tips"
        });
    },
});
