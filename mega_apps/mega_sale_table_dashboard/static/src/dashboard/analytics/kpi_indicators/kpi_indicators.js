/** @odoo-module */

import { Component } from "@odoo/owl";
import { formatCurrency } from "../../utils/format";

/**
 * Tarjetas de indicadores generales de la sección gráfica.
 *
 * OJO: aquí solo van métricas que NO existen ya en el KpiBanner de arriba
 * (Ventas con IVA / Subtotal / Facturas / Notas crédito). "Total vendido"
 * y "Subtotal vendido" se quitaron a propósito: el banner de arriba los
 * muestra en BRUTO (solo facturas), mientras que analytics.kpis los calcula
 * en NETO (facturas − notas crédito, la misma convención que ya usa el
 * desglose por asesor/cliente de la tabla) — mostrar ambos con la misma
 * etiqueta hacía parecer que el tablero se contradecía.
 */
export class KpiIndicators extends Component {
    static template = "mega_dashboard.KpiIndicators";
    static props = {
        kpis: { type: Object, optional: true },
        isLoading: { type: Boolean, optional: true },
    };

    get cards() {
        const k = this.props.kpis || {};
        return [
            {
                id: "clients",
                label: "Clientes",
                icon: "fa-users",
                color: "#9C27B0",
                display: formatCurrency(k.client_count || 0),
            },
            {
                id: "avg",
                label: "Promedio por documento (neto)",
                icon: "fa-line-chart",
                color: "#F39C12",
                display: "$ " + formatCurrency(k.avg_per_doc || 0, 0),
            },
            {
                id: "qty",
                label: "Unidades vendidas",
                icon: "fa-cubes",
                color: "#17A2B8",
                display: formatCurrency(k.total_qty || 0, 0),
            },
        ];
    }
}
