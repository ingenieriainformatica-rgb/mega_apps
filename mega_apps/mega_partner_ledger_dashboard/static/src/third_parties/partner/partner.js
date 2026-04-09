/** @odoo-module */

import { Component, useState, useRef } from "@odoo/owl";
import { useAutofocus } from "../utils";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { rpc } from "@web/core/network/rpc";

export class PartnerLedger extends Component {
    static template = "mega_partner_ledger_dashboard.PartnerLedger";

    static props = {
        partner: { type: Object, optional: true },
    };

    get partner() {
        if (!this.props || !this.props.partner) {
            return null;
        }

        // Validamos que sea objeto real
        if (typeof this.props.partner !== "object") {
            return null;
        }

        return this.props.partner;
    }

}
