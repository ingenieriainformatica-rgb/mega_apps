// /** @odoo-module **/

import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { BagCategory_list_popup } from "@sh_pos_all_in_one_retail/static/sh_pos_bag_charges/apps/popups/bag_category_list_popup/bag_category_list_popup";


patch(ControlButtons.prototype, {
    setup() {
        super.setup();
        this.showCarryButton = this.pos.config.sh_pos_bag_charges;
    },
    async onClickButton() {
        const pos_categ_id = this.pos.config.sh_carry_bag_category;
        const products = this.pos.models['product.product'].getAll().filter(product => product.pos_categ_ids.includes(pos_categ_id));
        const vals = await makeAwaitable(this.dialog, BagCategory_list_popup, { 'title': 'products', 'products': products });

    }



})

