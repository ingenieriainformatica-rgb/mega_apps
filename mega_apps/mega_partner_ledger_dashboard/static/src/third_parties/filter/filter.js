/** @odoo-module */

import { Component, useState, useRef } from "@odoo/owl";
import { useAutofocus } from "../utils";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { rpc } from "@web/core/network/rpc";

export class FilterThirdsLedger extends Component {
    static template = "mega_partner_ledger_dashboard.DateFilterBar";
    static components = { DateTimeInput };

    static props = {
        date_from: { optional: true }, // ✅ ahora pueden ser Date (no String)
        date_to: { optional: true },
        onSearch: { optional: true },
    };

    setup() {
        this.partnerInputRef = useRef("partnerInput");
        this.rpc = rpc; // ✅ usa servicio rpc en vez de import directo
        useAutofocus("partnerInput");

        this.state = useState({
            tipo: "all",
            partnerQuery: "",
            partnerResults: [],
            partnerSelected: null,
            error: "",
            // ✅ fechas editables en el hijo, inicializadas desde props
            date_from: this.props.date_from || false,
            date_to: this.props.date_to || false,
        });
    }

    async onPartnerInput(ev) {
        this.state.partnerQuery = ev.target.value;
        const q = (this.state.partnerQuery || "").trim();
        this.state.error = "";

        if (q.length < 2) {
            this.state.partnerResults = [];
            return;
        }

        const res = await this.rpc("/mega_partner_ledger/partner_autocomplete", {
            query: q,
            tipo: this.state.tipo,
            limit: 10,
        });

        if (!res.ok) {
            this.state.error = res.error || "Error desconocido en autocomplete";
            this.state.partnerResults = [];
            return;
        }

        this.state.partnerResults = res.data || [];
    }

    selectPartner(p) {
        this.state.partnerSelected = p;
        this.state.partnerQuery = p.name;
        this.state.partnerResults = [];
    }

    clearPartner() {
        this.state.partnerSelected = null;
        this.state.partnerQuery = "";
        this.state.partnerResults = [];
        // si estás usando t-ref="partnerInput" con useAutofocus, esto es opcional
        this.partnerInputRef?.el?.focus();
    }

    onDateFromChange(value) {
        this.state.date_from = value;
    }

    onDateToChange(value) {
        this.state.date_to = value;
    }

    onSearch() {
        if (!this.props.onSearch) return;

        // ✅ payload limpio (solo lo necesario)
        this.props.onSearch({
            partner: this.state.partnerSelected,
            tipo: this.state.tipo,
            date_from: this.state.date_from,
            date_to: this.state.date_to,
        });
    }
}
