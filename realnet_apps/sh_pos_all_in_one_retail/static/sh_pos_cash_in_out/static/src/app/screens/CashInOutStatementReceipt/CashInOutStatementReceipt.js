/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CashInOutStatementReceipt extends Component {
    static template = "sh_pos_all_in_one_retail.CashInOutStatementReceipt";
    setup() {
        super.setup();
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.printer = useService("printer");
    }
    tryReprint() {
        this.printer.print(
            this.constructor,
            this.props,
            { webPrintFallback: true }
        );
    }
}

registry.category("pos_screens").add("CashInOutStatementReceipt", CashInOutStatementReceipt);
