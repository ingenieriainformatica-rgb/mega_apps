    /** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype,  {
    redirectToBackend(){
        if (this.user && this.user.sh_is_direct_logout) {
            window.location  = "/web/session/logout";
        } else {
            super.redirectToBackend();
        }
    }
});

