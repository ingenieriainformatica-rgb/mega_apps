/** @odoo-module **/

// Oculta todas las apps del Home para Operarios excepto "Parqueo".
// No cambia grupos/menús en el servidor; es un filtro visual.

import { patch } from "@web/core/utils/patch";
import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";
import { onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";

const originalSetup = HomeMenu.prototype.setup;

patch(HomeMenu.prototype, {
    setup() {
        originalSetup.call(this, ...arguments);

        this.isOperator = false;

        onWillStart(async () => {
            try {
                this.isOperator = await user.hasGroup(
                    "odoo_parking_management.group_site_operator"
                );
            } catch (e) {
                this.isOperator = false;
            }
        });
    },

    get displayedApps() {
        const apps = this.props.apps || [];
        if (!this.isOperator) {
            return apps;
        }
        const allowedXmlids = new Set([
            "odoo_parking_management.parking_entry_menu_parking_management_root",
        ]);
        return apps.filter((app) => allowedXmlids.has(app.xmlid));
    },
});
