/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

// ── Componentes existentes (sin cambios) ─────────────────────────
import { DateFilterBar } from "../filter/filter";

// ── Componentes nuevos Sprint 1 ──────────────────────────────────
import { KpiBanner } from "../kpi_banner/kpi_banner";
import { KpiBannerSkeleton } from "../skeleton/skeleton";
import { getCurrentMonthRange } from "../utils/format";


export default class MegaSaleDashboard extends Component {
    static template = "mega_dashboard.SaleDashboard";
    static components = {
        Layout,
        DateFilterBar,
        KpiBanner,
        KpiBannerSkeleton,
    };
    static props = {
        action:            Object,
        actionId:          Number,
        updateActionState: Function,
        className:         { type: String, optional: true },
    };

    setup() {
        this.display     = { controlPanel: {} };
        this.statistics  = useState(useService("sales.statistics"));
        this.notification = useService("notification");
        this.actionService = useService("action");

        this.state = useState({
            loadingWarehouses: false,
            warehouses:        [],
            journals:          [],
            loadingJournals:   false,
            advisors:          [],
            loadingAdvisors:   false,
        });

        // Carga de sedes para el filtro (independiente del auto-load de datos)
        this.loadWarehouses();

        // Carga de asesores para el filtro (lista fija, no depende de sede/diario)
        this.loadAdvisors();

        // Auto-load: carga datos del mes actual al entrar al dashboard
        this._autoLoad();
    }

    // ─────────────────────────────────────────────────────────────
    // _autoLoad: carga el mes actual con todas las sedes y diarios.
    // Se ejecuta una sola vez al montar el componente.
    // ─────────────────────────────────────────────────────────────
    async _autoLoad() {
        const { date_from, date_to } = getCurrentMonthRange();
        await this.statistics.setRange({
            date_from,
            date_to,
            warehouse_id: "allHeadquarters",
            journal_id:   "allJournal",
            advisor_id:   "allAdvisors",
        });
    }

    // ─────────────────────────────────────────────────────────────
    // Carga la lista de sedes para el selector
    // ─────────────────────────────────────────────────────────────
    async loadWarehouses() {
        try {
            const res = await rpc("/mega_dashboard/get/warehouses", {});
            this.state.warehouses = res?.items || [];
            if (this.state.warehouses.length) {
                this.state.loadingWarehouses = true;
                // Precarga los diarios para "todas las sedes"
                this.onChangeWarehouse();
            }
        } catch (e) {
            this.notification.add("Error cargando almacenes.", { type: "danger" });
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Carga la lista de asesores para el selector (res.partner.is_advisor)
    // ─────────────────────────────────────────────────────────────
    async loadAdvisors() {
        try {
            const res = await rpc("/mega_dashboard/get/advisors", {});
            this.state.advisors = res?.items || [];
            this.state.loadingAdvisors = this.state.advisors.length > 0;
        } catch (e) {
            this.notification.add("Error cargando asesores.", { type: "danger" });
        }
    }

    // ─────────────────────────────────────────────────────────────
    // onClickFilter: recibe el payload del FilterBar y aplica.
    //
    // Cambios v2:
    // - Ya no bloquea por journal vacío (allJournal es válido).
    // - Mantiene validación de fechas.
    // ─────────────────────────────────────────────────────────────
    async onClickFilter(payload) {
        const date_from    = payload?.date_from;
        const date_to      = payload?.date_to;
        const warehouse_id = payload?.warehouse_id || "allHeadquarters";
        const journal_id   = payload?.journal_id   ?? null;
        const advisor_id   = payload?.advisor_id   ?? null;

        if (!date_from || !date_to) {
            this.notification.add(
                "Debes seleccionar 'Desde' y 'Hasta'.",
                { type: "warning" }
            );
            return;
        }

        if (date_to < date_from) {
            this.notification.add(
                "La fecha 'Hasta' no puede ser anterior a 'Desde'.",
                { type: "danger" }
            );
            return;
        }

        await this.statistics.setRange({ date_from, date_to, warehouse_id, journal_id, advisor_id });
    }

    // ─────────────────────────────────────────────────────────────
    // onChangeWarehouse: recarga la lista de diarios del selector
    // cuando cambia la sede seleccionada.
    // ─────────────────────────────────────────────────────────────
    async onChangeWarehouse(warehouse_id) {
        try {
            if (this.state.warehouses.length) {
                const res = await rpc("/mega_dashboard/get/journals", { warehouse_id });
                this.state.journals      = res?.items || [];
                this.state.loadingJournals = this.state.journals.length > 0;
            }
        } catch (e) {
            this.notification.add("Error cargando diarios del almacén.", { type: "danger" });
        }
    }

    openInvoice(ev) {
        const raw = ev.currentTarget?.dataset?.id;
        const invoiceId = raw ? parseInt(raw, 10) : NaN;

        if (!Number.isInteger(invoiceId) || invoiceId <= 0) {
            this.notification.add("ID de factura invalido.", { type: "warning" });
            return;
        }

        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: invoiceId,
            views: [[false, "form"]],
            view_mode: "form",
            target: "new",
        });
    }
}

registry.category("actions").add("realnet_sale_dashboard", MegaSaleDashboard);
