/** @odoo-module */

import { Component } from "@odoo/owl";
import { formatCurrency, calcDelta } from "../utils/format";

export class KpiBanner extends Component {
    static template = "mega_dashboard.KpiBanner";

    static props = {
        grand:          { type: Object, optional: true },
        grandRefunds:   { type: Object, optional: true },
        grandNet:       { type: Object, optional: true },
        previousPeriod: { type: Object, optional: true },
        isLoading:      { type: Boolean, optional: true },
    };

    // ─────────────────────────────────────────────────────────────
    // Calcula las 6 métricas del banner con sus deltas vs período anterior.
    // Se recalcula automáticamente cada vez que cambian los props.
    // ─────────────────────────────────────────────────────────────
    get metrics() {
        const g  = this.props.grand         || {};
        const r  = this.props.grandRefunds  || {};
        const n  = this.props.grandNet      || {};
        const pp = this.props.previousPeriod || {};
        const pg = pp.grand                 || {};
        const pr = pp.grand_refunds         || {};
        const pn = pp.grand_net             || {};

        // Período actual
        // Ventas Brutas = total CON IVA  (lo que paga el cliente)
        // Ventas Netas  = subtotal SIN IVA  (base gravable — coincide con "Subtotal" del Informe)
        // Ticket        = Ventas Netas / facturas  (precio neto promedio)
        // NC            = total CON IVA  (consistente con Ventas Brutas para el % NC)
        const ventas_brutas = g.total_sales || 0;
        const ventas_netas  = g.subtotal_untaxed || 0;
        const nc_total      = Math.abs(r.total_sales || 0);
        const count_inv     = g.count_invoices || 0;
        const ticket        = count_inv > 0 ? ventas_netas / count_inv : 0;
        const nc_pct        = ventas_brutas > 0 ? (nc_total / ventas_brutas) * 100 : 0;

        // Período anterior
        const prev_brutas   = pg.total_sales || 0;
        const prev_netas    = pg.subtotal_untaxed || 0;
        const prev_nc       = Math.abs(pr.total_sales || 0);
        const prev_count    = pg.count_invoices || 0;
        const prev_ticket   = prev_count > 0 ? prev_netas / prev_count : 0;
        const prev_nc_pct   = prev_brutas > 0 ? (prev_nc / prev_brutas) * 100 : 0;

        return [
            {
                id:       "ventas_brutas",
                label:    "Ventas Brutas",
                icon:     "fa-dollar",
                color:    "#1A3C6B",
                value:    ventas_brutas,
                display:  "$ " + formatCurrency(ventas_brutas, 2),
                delta:    calcDelta(ventas_brutas, prev_brutas),
                goodDir:  "up",   // verde cuando sube
            },
            {
                id:       "ventas_netas",
                label:    "Ventas Netas",
                icon:     "fa-check-circle",
                color:    "#7FB342",
                value:    ventas_netas,
                display:  "$ " + formatCurrency(ventas_netas, 2),
                delta:    calcDelta(ventas_netas, prev_netas),
                goodDir:  "up",
            },
            {
                id:       "facturas",
                label:    "Facturas",
                icon:     "fa-file-text-o",
                color:    "#1A3C6B",
                value:    count_inv,
                display:  formatCurrency(count_inv),
                delta:    calcDelta(count_inv, prev_count),
                goodDir:  "up",
            },
            {
                id:       "ticket",
                label:    "Ticket Promedio",
                icon:     "fa-tag",
                color:    "#5B6ABF",
                value:    ticket,
                display:  "$ " + formatCurrency(ticket, 2),
                delta:    calcDelta(ticket, prev_ticket),
                goodDir:  "up",
            },
            {
                id:       "nc_total",
                label:    "Notas Crédito",
                icon:     "fa-rotate-left",
                color:    "#C0392B",
                value:    nc_total,
                display:  "$ " + formatCurrency(nc_total, 2),
                delta:    calcDelta(nc_total, prev_nc),
                goodDir:  "down",  // verde cuando BAJA (menos NC = mejor)
            },
            {
                id:       "nc_pct",
                label:    "% NC",
                icon:     "fa-percent",
                color:    "#C0392B",
                value:    nc_pct,
                display:  nc_pct.toFixed(1) + "%",
                delta:    calcDelta(nc_pct, prev_nc_pct),
                goodDir:  "down",
            },
        ];
    }

    // Retorna true si la variación es "buena" según la dirección esperada del KPI
    isGoodDelta(metric) {
        if (metric.delta === null || metric.delta === undefined) return null;
        const isUp = metric.delta > 0;
        return metric.goodDir === "up" ? isUp : !isUp;
    }

    // Formatea el delta como string con signo (ej: "+12.4%" / "-3.1%")
    formatDelta(delta) {
        if (delta === null || delta === undefined) return null;
        const sign = delta > 0 ? "+" : "";
        return sign + delta.toFixed(1) + "%";
    }
}
