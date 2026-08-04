/** @odoo-module */

import { registry } from "@web/core/registry";
import { reactive } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { formatYMD, getCurrentMonthRange } from "./utils/format";

// ─────────────────────────────────────────────────────────────────
// Normalización de IDs — mantiene tokens "all*" tal cual,
// convierte números string a número, null/0/"" → null.
// ─────────────────────────────────────────────────────────────────
function parseIdOrAll(value) {
    if (value === null || value === undefined || value === "" || value === 0) return null;
    if (typeof value === "string" && value.startsWith("all")) return value;
    const n = Number(value);
    return Number.isFinite(n) && n !== 0 ? n : value;
}

// ─────────────────────────────────────────────────────────────────
// Normaliza el rango de fechas: completa con defaults y corrige
// inversiones (date_from > date_to).
// ─────────────────────────────────────────────────────────────────
function normalizeRange(range, fallback) {
    let date_from = (range && range.date_from) || fallback.date_from;
    let date_to = (range && range.date_to) || fallback.date_to;
    if (date_to < date_from) date_from = date_to;
    return { date_from, date_to };
}

// ─────────────────────────────────────────────────────────────────
// Servicio reactivo "sales.statistics"
// ─────────────────────────────────────────────────────────────────
const statisticsService = {
    start() {
        const def = getCurrentMonthRange();

        const statistics = reactive({
            // ── Estado de carga ──────────────────────────────────
            isReady: false,      // true una vez que los datos cargaron al menos una vez
            isLoading: false,    // true durante cualquier recarga (inicial o por filtro)

            // ── Rango y filtros activos ───────────────────────────
            isReadyWarehouse: false,
            date_from: def.date_from,
            date_to: def.date_to,
            warehouse_id: null,
            journal_id: null,
            advisor_id: null,
            company_id: null,
            state_filter: "posted",

            // ── Timer para auto-refresh (desactivado por defecto) ─
            _timer: null,

            // ─────────────────────────────────────────────────────
            // reload(): ejecuta el RPC con los parámetros actuales.
            // Si ya hay datos (isReady=true), los mantiene visibles
            // durante la recarga mostrando solo la barra de progreso.
            // ─────────────────────────────────────────────────────
            async reload() {
                this.isLoading = true;
                try {
                    const { date_from, date_to } = normalizeRange(
                        { date_from: this.date_from, date_to: this.date_to },
                        getCurrentMonthRange()
                    );
                    const warehouse_id = this.warehouse_id;
                    const journal_id = this.journal_id;
                    const advisor_id = this.advisor_id;
                    const company_id = this.company_id;
                    const state_filter = this.state_filter;

                    this.date_from = date_from;
                    this.date_to = date_to;

                    const updates = await rpc("/mega_dashboard/sales/statistics", {
                        date_from,
                        date_to,
                        warehouse_id,
                        journal_id,
                        advisor_id,
                        company_id,
                        state_filter,
                    });

                    Object.assign(this, updates, {
                        isReady: true,
                        isLoading: false,
                        isReadyWarehouse: !!warehouse_id && warehouse_id !== 0,
                    });
                } catch (e) {
                    console.error("sales.statistics reload error:", e);
                    this.isLoading = false;
                }
            },

            // ─────────────────────────────────────────────────────
            // setRange(): actualiza filtros y dispara recarga.
            // ─────────────────────────────────────────────────────
            async setRange({ date_from, date_to, warehouse_id, journal_id, advisor_id, company_id, state_filter }) {
                const norm = normalizeRange(
                    { date_from, date_to },
                    getCurrentMonthRange()
                );
                this.date_from = norm.date_from;
                this.date_to = norm.date_to;
                this.warehouse_id = parseIdOrAll(warehouse_id);
                this.journal_id = parseIdOrAll(journal_id);
                this.advisor_id = parseIdOrAll(advisor_id);
                this.company_id = parseIdOrAll(company_id);
                this.state_filter = state_filter || "posted";
                await this.reload();
            },

            // ─────────────────────────────────────────────────────
            // Auto-refresh (opcional, activar desde el componente)
            // ─────────────────────────────────────────────────────
            startAutoRefresh(ms = 60 * 1000) {
                if (this._timer) clearInterval(this._timer);
                this._timer = setInterval(() => this.reload(), ms);
            },

            stopAutoRefresh() {
                if (this._timer) clearInterval(this._timer);
                this._timer = null;
            },
        });

        return statistics;
    },
};

registry.category("services").add("sales.statistics", statisticsService);
