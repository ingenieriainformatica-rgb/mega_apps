/** @odoo-module */

import { Component, useState, onWillStart } from "@odoo/owl";
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

        this.display = {
            controlPanel: {},
        };

        this.statistics = useState(useService("sales.statistics"));

    }

    onClickFilter() {
        console.log("Llegaste al filtro");
    }

}

registry.category("actions").add("realnet_sale_dashboard", MegaSaleDashboard);
