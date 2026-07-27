/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useDateTimePicker } from "@web/core/datetime/datetime_hook";
import {
    getCurrentMonthRange,
    getCurrentWeekRange,
    getTodayRange,
} from "../utils/format";

const { DateTime } = luxon;

/**
 * FilterBarV2 — Barra de filtros del Dashboard Comercial v2.0.
 * Usa el DatePicker nativo de Odoo 18 para selección de fechas.
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

        const state = this.state;

        // ── Odoo DatePicker nativo para "Desde" ──────────────────
        this.dateFromPicker = useDateTimePicker({
            target: "dateFromAnchor",
            onApply: (date) => {
                this.state.date_from      = date.toFormat("yyyy-MM-dd");
                this.state.activeShortcut = "custom";
                if (this.state.date_from && this.state.date_to) this._emit();
            },
            get pickerProps() {
                return {
                    type:              "date",
                    value:             DateTime.fromISO(state.date_from),
                    showWeekNumbers:   false,
                    daysOfWeekFormat:  "narrow",
                };
            },
        });

        // ── Odoo DatePicker nativo para "Hasta" ──────────────────
        this.dateToPicker = useDateTimePicker({
            target: "dateToAnchor",
            onApply: (date) => {
                this.state.date_to        = date.toFormat("yyyy-MM-dd");
                this.state.activeShortcut = "custom";
                if (this.state.date_from && this.state.date_to) this._emit();
            },
            get pickerProps() {
                return {
                    type:              "date",
                    value:             DateTime.fromISO(state.date_to),
                    showWeekNumbers:   false,
                    daysOfWeekFormat:  "narrow",
                };
            },
        });
    }

    // ─────────────────────────────────────────────────────────────
    // Formatea ISO "2026-07-02" → "02/07/2026" para mostrar en botón
    // ─────────────────────────────────────────────────────────────
    formatDateDisplay(isoDate) {
        if (!isoDate) return "Seleccionar…";
        try {
            return DateTime.fromISO(isoDate).toFormat("dd/MM/yyyy");
        } catch {
            return isoDate;
        }
    }

    openDateFrom() { this.dateFromPicker.open(); }
    openDateTo()   { this.dateToPicker.open();   }

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
    // Emite el filtro actualizado al componente padre
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
