/** @odoo-module */

import { Component } from "@odoo/owl";
import { ChartCanvas } from "../chart_canvas/chart_canvas";
import { CHART_COLORS, formatCOP, formatCurrency, baseChartOptions, tickTruncate } from "../../utils/format";

/**
 * Top 30 productos/servicios más vendidos por cantidad (neta: facturado -
 * NC). Mismo estilo visual que "Ventas por asesor" (barras horizontales
 * ordenadas de mayor a menor). Componente reutilizado para dos gráficas
 * separadas -bienes con inventario vs servicios (mano de obra)-, ya que
 * mezclados en una sola lista los servicios (que se venden con cantidades
 * mucho más altas, 1 por técnico por orden) tapaban a los productos
 * reales con inventario.
 */
export class TopProductsChart extends Component {
    static template = "mega_dashboard.TopProductsChart";
    static components = { ChartCanvas };
    static props = {
        rows: { type: Array, optional: true },
        isLoading: { type: Boolean, optional: true },
        title: { type: String, optional: true },
        emptyLabel: { type: String, optional: true },
    };

    get rows() {
        return this.props.rows || [];
    }

    get config() {
        const rows = this.rows;
        if (!rows.length) return null;
        return {
            type: "bar",
            data: {
                labels: rows.map((r) => r.product),
                datasets: [
                    {
                        label: "Unidades vendidas",
                        data: rows.map((r) => r.qty),
                        backgroundColor: CHART_COLORS[3],
                        borderRadius: 4,
                        maxBarThickness: 18,
                    },
                ],
            },
            options: baseChartOptions({
                indexAxis: "y",
                scales: {
                    x: { ticks: { callback: (v) => formatCurrency(v, 0) } },
                    y: { ticks: { callback: tickTruncate(38) } },
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const r = rows[ctx.dataIndex];
                                return [
                                    "Unidades: " + formatCurrency(r.qty, 0),
                                    "Ingresos: " + formatCOP(r.revenue),
                                ];
                            },
                        },
                    },
                },
            }),
        };
    }
}
