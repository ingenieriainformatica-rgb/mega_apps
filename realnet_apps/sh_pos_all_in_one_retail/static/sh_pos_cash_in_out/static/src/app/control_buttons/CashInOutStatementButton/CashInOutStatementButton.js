/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { TransactionPopupWidget } from "@sh_pos_all_in_one_retail/static/sh_pos_cash_in_out/app/Popups/TransactionPopupWidget/TransactionPopupWidget";
import { CashInOutOptionStatementPopupWidget } from "@sh_pos_all_in_one_retail/static/sh_pos_cash_in_out/app/Popups/CashInOutOptionStatementPopupWidget/CashInOutOptionStatementPopupWidget";


patch(ControlButtons.prototype, {
    setup() {
        super.setup(...arguments)
        this.dialog = useService("dialog");
        this.pos = usePos();
    },
    async cash_in_out_statement() {
        const all_cash_in_out = this.pos.models['sh.cash.in.out'].readAll();
        const serializeddata = all_cash_in_out.map((each_statement) =>
            each_statement.serialize({ orm: true, clear: true })
        );
        await makeAwaitable(this.dialog, CashInOutOptionStatementPopupWidget, {
            title: _t("Payments"),
            'all_cash_in_out': serializeddata
        });
    },
    async sh_payments() {
        const all_payment = this.pos.models['pos.payment'].filter((payment) => payment.amount > 0);
        const serializedpaymentdata = all_payment.map((each_payment) =>
            each_payment.serialize({ orm: true, clear: true })
        );
        await makeAwaitable(this.dialog, TransactionPopupWidget, {
            title: _t("Payments"),
            'all_payment': serializedpaymentdata
        });
    }
})
