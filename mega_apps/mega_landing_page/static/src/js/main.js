/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { mount, whenReady } from "@odoo/owl";
import { MegaLeadForm } from "./mega_lead_form";
import { templates } from "@web/core/assets";

// Mount the MegaLeadForm component when the document.body is ready
whenReady(() => {
    mount(MegaLeadForm, document.body, { templates, dev: true, name: "MegaTecnicentro" });
});
