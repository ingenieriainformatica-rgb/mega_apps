/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { DashboardHero } from "../hero/hero";
import { DateFilterBar } from "../filter/filter";
import { Informe } from "../informe/informe";
import { InvoiceList } from "../InvoiceList/invoice_list";

export default class MegaSaleDashboard extends Component {
    static template = "mega_dashboard.SaleDashboard";
    static components = { Layout, DashboardHero, DateFilterBar, Informe, InvoiceList };
    static props = {
        action: Object,
        actionId: Number,
        updateActionState: Function,
        className: { type: String, optional: true },
    };

    setup() {
        this.display = { controlPanel: {} };
        this.statistics = useState(useService("sales.statistics"));
        this.notification = useService("notification");

        this.state = useState({
            loadingWarehouses: false,
            warehouses: [],
            journals: [],
            loadingJournals: false
        });

        this.loadWarehouses();
    }

    async loadWarehouses() {
        try {
            const res = await rpc("/mega_dashboard/get/warehouses", {});
            this.state.warehouses = res?.items || [];
            if (this.state.warehouses.length) {
                this.state.loadingWarehouses = true;
                this.onChangeWarehouse();
            }
        } catch (e) {
            this.notification.add("Error cargando almacenes.", { type: "danger" });
        }
    }

    async onClickFilter(payload) {
        const date_from = payload?.date_from;
        const date_to = payload?.date_to;
        const warehouse_id = payload?.warehouse_id || [];

        // lo normal es que journal sea string (id) o null/""
        const journal_id = payload?.journal_id ?? payload?.journal ?? null;

        const noJournalSelected =
            journal_id === null ||
            journal_id === undefined ||
            journal_id === "" ||
            journal_id === "0";

        if (noJournalSelected) {
            this.notification.add("Selecciona un diario (o no hay diarios para esa sede).", { type: "warning" });
            return;
        }

        if (warehouse_id == "") {
            this.notification.add("No tienes sedes registradas, contacta el administrador", { type: "danger" });
            return;
        }

        if (!date_from || !date_to) {
            this.notification.add("Debes seleccionar 'Desde' y 'Hasta'.", { type: "warning" });
            return;
        }

        if (date_to < date_from) {
            this.notification.add(
                "Rango inválido: la fecha 'Hasta' no puede ser menor que la fecha 'Desde'.",
                { type: "danger" }
            );
            return;
        }

        if (typeof this.statistics.setRange === "function") {
            await this.statistics.setRange({ date_from, date_to, warehouse_id, journal_id });
            return;
        }
    }

    // ✅ ONCHANGE (desde DateFilterBar)
    async onChangeWarehouse(warehouse_id) {
        try {
            if (this.state.warehouses.length) {
                const res = await rpc("/mega_dashboard/get/journals", { warehouse_id });
                this.state.journals = res?.items || [];
                if (this.state.journals.length) {
                    this.state.loadingJournals = true;
                }else{
                    this.state.loadingJournals = false;
                }
            }
        } catch (e) {
            this.notification.add("Error cargando diarios del almacén.", { type: "danger" });
        }
    }

}

registry.category("actions").add("realnet_sale_dashboard", MegaSaleDashboard);
