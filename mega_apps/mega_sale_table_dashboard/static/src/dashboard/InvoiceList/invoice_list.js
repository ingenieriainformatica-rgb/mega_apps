/** @odoo-module */
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";


export class InvoiceList extends Component {
    static template = "mega_dashboard.InvoiceList";
    static props = {
        invoicesList: { type: Array, optional: true }, // ✅ Array y optional
    };

    setup() {
        this.actionService = useService("action"); // ✅ nombre distinto para evitar confusiones
    }

    get invoices() {
        return this.props.invoicesList || [];
    }

    openInvoice(ev) {
        const raw = ev.currentTarget?.dataset?.id;
        const invoiceId = raw ? parseInt(raw, 10) : NaN;

        if (!Number.isInteger(invoiceId) || invoiceId <= 0) {
            this.notification?.add("ID de factura inválido.", { type: "warning" });
            return;
        }

        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: invoiceId, // ✅ número
            views: [[false, "form"]],
            view_mode: "form",
            target: "new",
        });
    }



}
