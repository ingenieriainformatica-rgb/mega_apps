/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";
import { DashboardHero } from "../hero/hero";
import { DateFilterBar } from "../filter/filter";
import { Informe } from "../informe/informe";

export default class MegaSaleDashboard extends Component {
    static template = "mega_dashboard.SaleDashboard";
    static components = { Layout, DashboardHero, DateFilterBar, Informe };
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
        console.log("Statistics -> ", this.statistics);
    }

    async onClickFilter(payload) {
        const date_from = payload?.date_from;
        const date_to = payload?.date_to;

        // ✅ Validación básica
        if (!date_from || !date_to) {
            this.notification.add("Debes seleccionar 'Desde' y 'Hasta'.", { type: "warning" });
            return;
        }

        // ✅ Si date_to < date_from (formato YYYY-MM-DD se puede comparar como string)
        if (date_to < date_from) {
            this.notification.add(
                "Rango inválido: la fecha 'Hasta' no puede ser menor que la fecha 'Desde'.",
                { type: "danger" }
            );
            return; // ⛔ NO aplicar filtro
        }

        // ✅ Si pasa la validación, manda al service (si ya tienes setRange)
        if (typeof this.statistics.setRange === "function") {
            await this.statistics.setRange({ date_from, date_to });
            return;
        }
    }
}

registry.category("actions").add("realnet_sale_dashboard", MegaSaleDashboard);
