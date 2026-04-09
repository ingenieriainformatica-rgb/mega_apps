/** @odoo-module */

import { Component } from "@odoo/owl";

export class ListLedger extends Component {
    static template = "mega_partner_ledger_dashboard.ListLedger";

    static props = {
        invoices: { type: Array, optional: true }, // 👈 es un Array
    };

    get invoices_list() {
        return Array.isArray(this.props?.invoices) ? this.props.invoices : [];
    }
}
