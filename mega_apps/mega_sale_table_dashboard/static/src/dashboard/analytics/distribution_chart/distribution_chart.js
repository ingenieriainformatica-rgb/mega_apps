/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { ChartCanvas } from "../chart_canvas/chart_canvas";
import { CHART_COLORS, formatCOP, baseChartOptions } from "../../utils/format";

/** Dimensiones candidatas. Solo se ofrecen como pestaña si el backend
 * trajo filas para esa dimensión -evita pestañas vacías por datos que
 * no existen en esta instalación (p.ej. sin categorías reales)-. */
const DIMENSIONS = [
    { key: "by_warehouse", label: "Sede" },
    { key: "by_team", label: "Equipo" },
    { key: "by_doc_type", label: "Tipo de documento" },
    { key: "by_category", label: "Categoría" },
];

function rowValue(row) {
    return row.total_sales !== undefined ? row.total_sales : row.subtotal_untaxed || 0;
}

export class DistributionChart extends Component {
    static template = "mega_dashboard.DistributionChart";
    static components = { ChartCanvas };
    static props = {
        distribution: { type: Object, optional: true },
        isLoading: { type: Boolean, optional: true },
    };

    setup() {
        this.state = useState({ dimension: "by_warehouse" });
    }

    get availableDimensions() {
        const dist = this.props.distribution || {};
        return DIMENSIONS.filter((d) => (dist[d.key] || []).length > 0);
    }

    selectDimension(key) {
        this.state.dimension = key;
    }

    get activeRows() {
        const dist = this.props.distribution || {};
        const available = this.availableDimensions;
        const active = available.some((d) => d.key === this.state.dimension)
            ? this.state.dimension
            : (available[0] && available[0].key);
        return dist[active] || [];
    }

    get config() {
        const rows = this.activeRows.slice(0, 10);
        if (!rows.length) return null;
        return {
            type: "doughnut",
            data: {
                labels: rows.map((r) => r.label),
                datasets: [
                    {
                        data: rows.map((r) => rowValue(r)),
                        backgroundColor: rows.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]),
                        borderWidth: 1,
                        borderColor: "#fff",
                    },
                ],
            },
            options: baseChartOptions({
                plugins: {
                    legend: { display: true, position: "right", labels: { boxWidth: 10, font: { size: 10 } } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const r = rows[ctx.dataIndex];
                                const parts = [(r.label || "") + ": " + formatCOP(rowValue(r))];
                                if (r.count_docs !== undefined) parts.push("Documentos: " + r.count_docs);
                                if (r.qty !== undefined) parts.push("Unidades: " + r.qty);
                                return parts;
                            },
                        },
                    },
                },
            }),
        };
    }
}
