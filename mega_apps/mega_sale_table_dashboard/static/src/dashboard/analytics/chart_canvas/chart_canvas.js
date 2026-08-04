/** @odoo-module */

import { Component, useRef, onWillStart, onWillUnmount, useEffect } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";

/**
 * Envoltorio genérico de Chart.js para todo el tablero. Chart.js se carga
 * mediante el bundle oficial de asssets de Odoo (web.chartjs_lib) -no hay
 * referencias manuales a rutas de debug ni CDN externo-, y esta es la
 * ÚNICA pieza del módulo que crea/destruye instancias de Chart, así que
 * el ciclo de vida (destruir antes de reconstruir, destruir al desmontar)
 * queda garantizado en un solo lugar para las 4 gráficas del tablero.
 *
 * Prop `config`: objeto {type, data, options} listo para `new Chart(...)`.
 * Si `config` es null/undefined, se muestra el estado vacío/"sin datos".
 */
export class ChartCanvas extends Component {
    static template = "mega_dashboard.ChartCanvas";
    static props = {
        config: { type: Object, optional: true },
        title: { type: String, optional: true },
        isLoading: { type: Boolean, optional: true },
        emptyLabel: { type: String, optional: true },
        height: { type: Number, optional: true },
    };

    setup() {
        this.canvasRef = useRef("canvas");
        this.chart = null;

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
        });

        useEffect(
            () => {
                this._renderOrDestroy();
            },
            () => [this.props.config, this.canvasRef.el]
        );

        onWillUnmount(() => this._destroyChart());
    }

    get hasData() {
        const cfg = this.props.config;
        if (!cfg || !cfg.data || !Array.isArray(cfg.data.datasets)) return false;
        return cfg.data.datasets.some((ds) => Array.isArray(ds.data) && ds.data.length);
    }

    _destroyChart() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
    }

    _renderOrDestroy() {
        // Siempre se destruye la instancia anterior antes de crear una
        // nueva (evita gráficas fantasma/fugas de memoria al refiltrar).
        this._destroyChart();
        if (!this.canvasRef.el || !this.hasData) {
            return;
        }
        // eslint-disable-next-line no-undef
        this.chart = new Chart(this.canvasRef.el, this.props.config);
    }
}
