/** @odoo-module */
    

import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/store/pos_hook";
   
export class ShortcutTipsPopup extends Component {
    static components = {  Dialog };
    static template = 'sh_pos_keyboard_shortcut.ShortcutTipsPopup';

        setup() {
            super.setup();
            this.pos = usePos();
        }
        close() {
            this.props.close();
        }
    }
