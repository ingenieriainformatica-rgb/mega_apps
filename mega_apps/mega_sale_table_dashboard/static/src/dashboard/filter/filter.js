/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import {
    formatYMD,
    getCurrentMonthRange,
    getCurrentWeekRange,
    getTodayRange,
} from "../utils/format";

/**
 * FilterBarV2 — Barra de filtros inteligente del Dashboard Comercial v2.0.
 *
 * Cambios vs v1:
 * - Sin botón "Filtrar": cada cambio aplica inmediatamente (onchange).
 * - Shortcuts de período: Hoy / Esta semana / Este mes / Personalizado.
 * - Default: mes actual (no los últimos 7 días).
 * - Unificada la clave enviada al padre: siempre "journal_id" (no "journal").
 * - Corrección del bug last30Days() (fecha_from = fecha_to − 0 días).
 */
export class DateFilterBar extends Component {
    static template = "mega_dashboard.DateFilterBar";

    static props = {
        onChangeWarehouse: { type: Function, optional: true },
        onClickFilter:     { type: Function },
        warehouses:        { type: Array,   optional: true },
        loadingWarehouses: { type: Boolean, optional: true },
        journals:          { type: Array,   optional: true },
        loadingJournals:   { type: Boolean, optional: true },
    };

    setup() {
        const def = getCurrentMonthRange();

        this.state = useState({
            date_from:      def.date_from,
            date_to:        def.date_to,
            warehouse_id:   "allHeadquarters",
            journal_id:     "allJournal",
            activeShortcut: "month",
        });
    }

    // ─────────────────────────────────────────────────────────────
    // Shortcuts de período
    // ─────────────────────────────────────────────────────────────
    get shortcuts() {
        return [
            { key: "today",  label: "Hoy" },
            { key: "week",   label: "Esta semana" },
            { key: "month",  label: "Este mes" },
            { key: "custom", label: "Período" },
        ];
    }

    applyShortcut(key) {
        if (key === "custom") {
            // Solo activa el modo fecha libre; no recarga hasta que el usuario
            // termine de ingresar ambas fechas.
            this.state.activeShortcut = "custom";
            return;
        }

        let range;
        switch (key) {
            case "today": range = getTodayRange();        break;
            case "week":  range = getCurrentWeekRange();  break;
            default:      range = getCurrentMonthRange(); break;
        }

        this.state.date_from      = range.date_from;
        this.state.date_to        = range.date_to;
        this.state.activeShortcut = key;
        this._emit();
    }

    // ─────────────────────────────────────────────────────────────
    // Cambio de sede → resetea diario → recarga
    // ─────────────────────────────────────────────────────────────
    onChangeWarehouse(ev) {
        const val = ev.target.value || "allHeadquarters";
        this.state.warehouse_id = val;
        this.state.journal_id   = "allJournal";

        if (this.props.onChangeWarehouse) {
            this.props.onChangeWarehouse(val);
        }
        this._emit();
    }

    // ─────────────────────────────────────────────────────────────
    // Cambio de diario → recarga
    // ─────────────────────────────────────────────────────────────
    onChangeJournal(ev) {
        this.state.journal_id = ev.target.value || "allJournal";
        this._emit();
    }

    // ─────────────────────────────────────────────────────────────
    // Cambio de fecha → recarga solo si ambas fechas están completas
    // ─────────────────────────────────────────────────────────────
    onChangeDateFrom(ev) {
        this.state.date_from      = ev.target.value;
        this.state.activeShortcut = "custom";
        if (this.state.date_from && this.state.date_to) this._emit();
    }

    onChangeDateTo(ev) {
        this.state.date_to        = ev.target.value;
        this.state.activeShortcut = "custom";
        if (this.state.date_from && this.state.date_to) this._emit();
    }

    // ─────────────────────────────────────────────────────────────
    // Emite el filtro al componente padre
    // ─────────────────────────────────────────────────────────────
    _emit() {
        this.props.onClickFilter({
            date_from:    this.state.date_from,
            date_to:      this.state.date_to,
            warehouse_id: this.state.warehouse_id,
            journal_id:   this.state.journal_id,
        });
    }
}
