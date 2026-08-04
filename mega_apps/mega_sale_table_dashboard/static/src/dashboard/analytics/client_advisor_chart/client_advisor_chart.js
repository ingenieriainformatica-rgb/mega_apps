/** @odoo-module */

import { Component } from "@odoo/owl";
import { ChartCanvas } from "../chart_canvas/chart_canvas";
import { CHART_COLORS, formatCOP, baseChartOptions, tickTruncate } from "../../utils/format";

const MAX_ADVISORS = 8;

/**
 * Ventas por empresa (cliente facturado) y asesor: barras apiladas,
 * X = top clientes por facturación dentro del filtro activo, cada barra
 * desglosada por asesor.
 *
 * "Empresa" aquí es el cliente/contacto facturado (partner_id), p.ej.
 * rentings, aseguradoras, flotas corporativas, o personas naturales según
 * la sede. El backend (analytics.py) ya limita a los clientes con más
 * facturación dentro del filtro actual (sede/diario/asesor/fecha), así que
 * si se filtra por una sede específica, esta gráfica muestra los
 * principales clientes DE ESA SEDE, no los del negocio completo.
 */
export class ClientAdvisorChart extends Component {
    static template = "mega_dashboard.ClientAdvisorChart";
    static components = { ChartCanvas };
    static props = {
        rows: { type: Array, optional: true },
        isLoading: { type: Boolean, optional: true },
    };

    get pivot() {
        const rows = this.props.rows || [];
        // Clientes ya vienen acotados desde el backend; se preserva el
        // orden de mayor a menor facturación total.
        const clients = [...new Set(rows.map((r) => r.client || "Sin cliente"))];

        const totalsByAdvisor = {};
        for (const r of rows) {
            totalsByAdvisor[r.advisor] = (totalsByAdvisor[r.advisor] || 0) + r.total_sales;
        }
        const advisors = Object.keys(totalsByAdvisor)
            .sort((a, b) => totalsByAdvisor[b] - totalsByAdvisor[a])
            .slice(0, MAX_ADVISORS);
        const advisorSet = new Set(advisors);

        const datasets = advisors.map((advisor, ai) => {
            const data = new Array(clients.length).fill(0);
            const counts = new Array(clients.length).fill(0);
            for (const r of rows) {
                if (r.advisor !== advisor) continue;
                const idx = clients.indexOf(r.client || "Sin cliente");
                if (idx === -1) continue;
                data[idx] += r.total_sales;
                counts[idx] += r.count_docs;
            }
            return {
                label: advisor,
                data,
                counts,
                backgroundColor: CHART_COLORS[ai % CHART_COLORS.length],
                borderRadius: 4,
            };
        });

        // Asesores fuera del top se agrupan en "Otros" para no perder el
        // total del cliente en la gráfica.
        const othersData = clients.map((client, idx) => {
            let sum = 0;
            let count = 0;
            for (const r of rows) {
                if ((r.client || "Sin cliente") !== client || advisorSet.has(r.advisor)) continue;
                sum += r.total_sales;
                count += r.count_docs;
            }
            return { sum, count };
        });
        if (othersData.some((o) => o.sum)) {
            datasets.push({
                label: "Otros asesores",
                data: othersData.map((o) => o.sum),
                counts: othersData.map((o) => o.count),
                backgroundColor: "#B0BEC5",
                borderRadius: 4,
            });
        }

        return { clients, datasets };
    }

    get config() {
        const { clients, datasets } = this.pivot;
        if (!clients.length) return null;
        return {
            type: "bar",
            data: { labels: clients, datasets },
            options: baseChartOptions({
                scales: {
                    x: { stacked: true, ticks: { callback: tickTruncate(16) } },
                    y: { stacked: true, ticks: { callback: (v) => formatCOP(v) } },
                },
                plugins: {
                    legend: { display: true, labels: { boxWidth: 12, font: { size: 11 } } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const ds = ctx.dataset;
                                const count = ds.counts ? ds.counts[ctx.dataIndex] : null;
                                const base = ds.label + ": " + formatCOP(ctx.parsed.y);
                                return count != null ? [base, "Documentos: " + count] : base;
                            },
                        },
                    },
                },
            }),
        };
    }
}
