/** @odoo-module */

import { Component } from "@odoo/owl";
import { ChartCanvas } from "../chart_canvas/chart_canvas";
import { CHART_COLORS, formatCOP, baseChartOptions } from "../../utils/format";

const { DateTime } = luxon;

const GRANULARITY_LABEL = { day: "Diaria", week: "Semanal", month: "Mensual" };

function formatBucketLabel(isoDate, granularity) {
    const dt = DateTime.fromISO(isoDate);
    if (!dt.isValid) return isoDate;
    if (granularity === "month") return dt.toFormat("MMM yyyy");
    if (granularity === "week") return "Sem " + dt.toFormat("dd/MM");
    return dt.toFormat("dd/MM");
}

/**
 * Evolución de ventas en el tiempo. La granularidad (día/semana/mes) la
 * decide el backend según el tamaño del rango de fechas seleccionado
 * (ver analytics._pick_granularity) para que la gráfica siga siendo
 * legible tanto para "hoy" como para "todo el año".
 */
export class EvolutionChart extends Component {
    static template = "mega_dashboard.EvolutionChart";
    static components = { ChartCanvas };
    static props = {
        timeseries: { type: Object, optional: true },
        isLoading: { type: Boolean, optional: true },
    };

    get granularityLabel() {
        const g = this.props.timeseries && this.props.timeseries.granularity;
        return GRANULARITY_LABEL[g] || "";
    }

    get config() {
        const ts = this.props.timeseries || {};
        const points = ts.points || [];
        if (!points.length) return null;
        const granularity = ts.granularity || "day";

        return {
            type: "line",
            data: {
                labels: points.map((p) => formatBucketLabel(p.date, granularity)),
                datasets: [
                    {
                        label: "Ventas netas",
                        data: points.map((p) => p.total_sales),
                        borderColor: CHART_COLORS[0],
                        backgroundColor: "rgba(26, 60, 107, .12)",
                        fill: true,
                        tension: 0.3,
                        pointRadius: 3,
                    },
                ],
            },
            options: baseChartOptions({
                scales: { y: { ticks: { callback: (v) => formatCOP(v) } } },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const p = points[ctx.dataIndex];
                                return [
                                    "Ventas: " + formatCOP(p.total_sales),
                                    "Documentos: " + p.count_docs,
                                ];
                            },
                        },
                    },
                },
            }),
        };
    }
}
