/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { Layout } from "@web/search/layout";
import { FilterThirdsLedger } from "./filter/filter";
import { useService } from "@web/core/utils/hooks";
import { deserializeDate, serializeDate } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import { PartnerLedger } from "./partner/partner";
import { ListLedger } from "./list/list"


export default class PartnerLedgerApp extends Component {
    static template = "mega_partner_ledger_dashboard.ShowLedger";
    static components = { Layout, FilterThirdsLedger, PartnerLedger, ListLedger };
    static props = {
        action: { type: Object, optional: true },
        actionId: { type: Number, optional: true },
        className: { type: String, optional: true },
        updateActionState: { type: Function, optional: true },
    };

    setup() {
        this.action = useService("action");
        this.notify = useService("notification");
        this.rpc = rpc; // ✅ usa servicio rpc en vez de import directo

        this.display = { controlPanel: {} };

        const { firstDay, lastDay } = this._getDefaultMonthRange();

        this.state = useState({
            ok: false,
            loading: false,
            error: "",
            // ✅ filtros "oficiales" (single source of truth)
            filters: {
                tipo: "all",
                partner: null,
                date_from: deserializeDate(firstDay),
                date_to: deserializeDate(lastDay),
            },
            // resultados
            accounts: [],
            invoices: [],
            partner: null,
        });
    }

    _getDefaultMonthRange() {
        const today = new Date();
        const iso = (d) => d.toISOString().slice(0, 10);
        const firstDay = iso(new Date(today.getFullYear(), today.getMonth(), 1));
        const lastDay = iso(new Date(today.getFullYear(), today.getMonth() + 1, 0));
        return { firstDay, lastDay };
    }

    openContacts() {
        this.action.doAction("base.action_partner_form");
    }

    /**
     * Recibe payload limpio del hijo:
     * { partner, tipo, date_from, date_to }
     */
    async onSearch(payload) {
        const { partner, date_from, date_to, tipo } = payload || {};

        if (!partner?.id) {
            this.notify.add("Debe seleccionar un tercero (Nombre / NIT / Documento).", { type: "danger" });
            return;
        }
        if (!date_from || !date_to) {
            this.notify.add("Debe seleccionar el rango de fechas (Desde / Hasta).", { type: "danger" });
            return;
        }
        // opcional: validar orden
        if (date_from > date_to) {
            this.notify.add("La fecha 'Desde' no puede ser mayor que 'Hasta'.", { type: "danger" });
            return;
        }

        // ✅ guarda filtros oficiales
        this.state.filters = { partner, tipo, date_from, date_to };

        await this._loadLedger();
    }

    async _loadLedger() {
        this.state.loading = true;
        this.state.error = "";

        try {
            const { partner, tipo, date_from, date_to } = this.state.filters;

            const data = {
                documento: partner.id,
                date_from: serializeDate(date_from),
                date_to: serializeDate(date_to),
            };

            // 🔁 EJEMPLO: llama tu endpoint del ledger (ajusta ruta y payload)
            const res = await this.rpc("/rn_partner_ledger/search", data);
            this.state.ok = res?.ok || false;
            this.state.partner = res?.data?.partner || null;
            // this.state.accounts = res?.accounts || [];
            this.state.invoices = res?.data?.moves || [];
            console.log("Respuesta ---->>>> ", this.state)
        } catch (e) {
            console.error(e);
            this.state.error = "No fue posible cargar el ledger.";
            this.notify.add(this.state.error, { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    exportExcel() {
        const moves = this.state.invoices;
        if (!Array.isArray(moves) || !moves.length) {
            this.notify.add("No hay resultados para exportar. Ejecuta una consulta primero.", { type: "warning" });
            return;
        }

        const { partner, date_from, date_to } = this.state.filters || {};
        if (!partner?.id || !date_from || !date_to) {
            this.notify.add("Faltan filtros para exportar (tercero y fechas).", { type: "danger" });
            return;
        }

        const params = new URLSearchParams({
            documento: partner.id,
            date_from: serializeDate(date_from),
            date_to: serializeDate(date_to),
        });

        // ✅ ruta correcta (sin /web)
        window.open(`/mega_partner_ledger/export?${params.toString()}`, "_blank");
    }

}

registry
    .category("actions")
    .add("mega_partner_ledger_dashboard.mega_partner_ledger_dashboard_ledger", PartnerLedgerApp);
