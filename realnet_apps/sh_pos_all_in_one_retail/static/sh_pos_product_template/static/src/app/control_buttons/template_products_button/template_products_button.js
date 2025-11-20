/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";


patch(ControlButtons.prototype, {
    async onClickTemplateLoad(){
        var templates = await this.pos.models['pos.product.template'].getAll()
        this.pos.showScreen("TemplateProductsListScreenWidget");
        // this.pos.showScreen("TemplateProductsListScreenWidget", {
        //     'templates': templates
        // });
    }
})