/** @odoo-module */

import { Component } from "@odoo/owl";
import { formatCurrency } from "../utils/format";

export class KpiBanner extends Component {
    static template = "mega_dashboard.KpiBanner";

    static props = {
        grand:          { type: Object, optional: true },
        grandRefunds:   { type: Object, optional: true },
        grandNet:       { type: Object, optional: true },
        previousPeriod: { type: Object, optional: true },
        isLoading:      { type: Boolean, optional: true },
    };

    get metrics() {
        const g = this.props.grand        || {};
        const r = this.props.grandRefunds || {};

        // Ventas con IVA  = total_sales (lo que paga el cliente)
        // Subtotal        = subtotal_untaxed (base gravable, coincide con Informe)
        // NC con IVA      = total_sales de notas crédito (valor con IVA)
        // NC Subtotal     = subtotal_untaxed de notas crédito (coincide con Informe)
        const ventas_brutas = g.total_sales || 0;
        const ventas_netas  = g.subtotal_untaxed || 0;
        const count_inv     = g.count_invoices || 0;
        const nc_iva        = Math.abs(r.total_sales || 0);
        const nc_subtotal   = Math.abs(r.subtotal_untaxed || 0);
        const nc_count      = r.count_invoices || 0;

        return [
            {
                id:      "ventas_brutas",
                label:   "Ventas con IVA",
                icon:    "fa-dollar",
                color:   "#1A3C6B",
                display: "$ " + formatCurrency(ventas_brutas, 2),
            },
            {
                id:      "ventas_netas",
                label:   "Subtotal",
                icon:    "fa-check-circle",
                color:   "#7FB342",
                display: "$ " + formatCurrency(ventas_netas, 2),
            },
            {
                id:      "facturas",
                label:   "Facturas",
                icon:    "fa-file-text-o",
                color:   "#1A3C6B",
                display: formatCurrency(count_inv),
            },
            {
                id:      "nc_iva",
                label:   "Notas Crédito IVA",
                icon:    "fa-rotate-left",
                color:   "#C0392B",
                display: "-$ " + formatCurrency(nc_iva, 2),
            },
            {
                id:      "nc_subtotal",
                label:   "Notas Crédito Subtotal",
                icon:    "fa-rotate-left",
                color:   "#C0392B",
                display: "-$ " + formatCurrency(nc_subtotal, 2),
            },
            {
                id:      "nc_count",
                label:   "Total Notas Crédito",
                icon:    "fa-hashtag",
                color:   "#C0392B",
                display: formatCurrency(nc_count),
            },
        ];
    }
}
