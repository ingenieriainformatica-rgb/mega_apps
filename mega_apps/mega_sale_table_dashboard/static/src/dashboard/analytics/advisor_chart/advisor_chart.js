/** @odoo-module */

import { Component } from "@odoo/owl";
import { ChartCanvas } from "../chart_canvas/chart_canvas";
import { CHART_COLORS, formatCOP, baseChartOptions, tickTruncate } from "../../utils/format";

const MAX_ADVISORS = 15;

/** Ventas por asesor: barras horizontales, ya vienen ordenadas de mayor
 * a menor desde el backend (analytics.by_advisor). */
export class AdvisorChart extends Component {
    static template = "mega_dashboard.AdvisorChart";
    static components = { ChartCanvas };
    static props = {
        rows: { type: Array, optional: true },
        isLoading: { type: Boolean, optional: true },
    };

    get rows() {
        return (this.props.rows || []).slice(0, MAX_ADVISORS);
    }

    get config() {
        const rows = this.rows;
        if (!rows.length) return null;
        return {
            type: "bar",
            data: {
                labels: rows.map((r) => r.advisor),
                datasets: [
                    {
                        label: "Total vendido",
                        data: rows.map((r) => r.total_sales),
                        backgroundColor: CHART_COLORS[0],
                        borderRadius: 4,
                        maxBarThickness: 26,
                    },
                ],
            },
            options: baseChartOptions({
                indexAxis: "y",
                scales: {
                    x: { ticks: { callback: (v) => formatCOP(v) } },
                    y: { ticks: { callback: tickTruncate(22) } },
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const r = rows[ctx.dataIndex];
                                return [
                                    "Total: " + formatCOP(r.total_sales),
                                    "Documentos confirmados: " + r.count_docs,
                                    "Promedio: " + formatCOP(r.avg_per_doc),
                                ];
                            },
                        },
                    },
                },
            }),
        };
    }
}
