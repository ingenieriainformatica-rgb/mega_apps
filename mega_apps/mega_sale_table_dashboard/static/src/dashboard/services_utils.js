/** @odoo-module */

import { registry } from "@web/core/registry";
import { reactive } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

function formatYMD(dateObj) {
  const y = dateObj.getFullYear();
  const m = String(dateObj.getMonth() + 1).padStart(2, "0");
  const d = String(dateObj.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

// Default: últimos 7 días (puedes cambiar a inicio de mes)
function getDefaultRange() {
  const today = new Date();
  const from = new Date(today);
  from.setDate(today.getDate() - 7);
  return { date_from: formatYMD(from), date_to: formatYMD(today) };
}

// Normaliza (evita null, corrige from/to)
function normalizeRange(range) {
  const def = getDefaultRange();
  let date_from = range?.date_from || def.date_from;
  let date_to = range?.date_to || def.date_to;

  // Si quedan invertidas
  if (date_to < date_from) {
    date_from = date_to;
  }
  return { date_from, date_to };
}

function parseIdOrAll(value) {
  if (value === null || value === undefined || value === "") return null;

  // si viene un "all..." lo dejamos tal cual
  if (typeof value === "string" && value.startsWith("all")) return value;

  // si viene número en string ("12") o número (12)
  const n = Number(value);
  return Number.isFinite(n) ? n : value; // fallback: deja el string si no es número
}

const statisticsService = {
  start() {
    const def = getDefaultRange();

    const statistics = reactive({
      isReady: false,
      isReadyWarehouse: false,
      date_from: def.date_from,
      date_to: def.date_to,
      warehouse_id: null,
      journal_id: null,

      // aquí quedarán tus datos del endpoint
      kpis: {},
      sedes: [],
      top_customers: [],
      top_products: [],
      conversion: {},

      _timer: null,

      async reload() {
        try {
          const { date_from, date_to } = normalizeRange({
            date_from: this.date_from,
            date_to: this.date_to,
          });

          const warehouse_id = this.warehouse_id
          const journal_id =  this.journal_id

          // Persistimos el rango normalizado
          this.date_from = date_from;
          this.date_to = date_to;

          const updates = await rpc("/mega_dashboard/sales/statistics", {date_from, date_to, warehouse_id, journal_id});

          Object.assign(this, updates, {
            isReady: true,
            isReadyWarehouse: warehouse_id != 0,
          });

        } catch (e) {
          console.error("sales.statistics reload error:", e);
        }
      },

      // ✅ ESTE ES EL QUE TE FALTA
      async setRange({ date_from, date_to, warehouse_id, journal_id }) {
        const norm = normalizeRange({ date_from, date_to });
        this.date_from = norm.date_from;
        this.date_to = norm.date_to;
        this.warehouse_id = parseIdOrAll(warehouse_id);
        this.journal_id = parseIdOrAll(journal_id);
        await this.reload();
      },

      startAutoRefresh(ms = 60 * 1000) {
        if (this._timer) clearInterval(this._timer);
          this._timer = setInterval(() => this.reload(), ms);
      },

      stopAutoRefresh() {
        if (this._timer) clearInterval(this._timer);
        this._timer = null;
      },
    });

    // Primera carga
    statistics.reload();
    // Auto refresh (recarga con el rango ACTUAL)
    statistics.startAutoRefresh(60 * 1000);

    return statistics;
  },
};

registry.category("services").add("sales.statistics", statisticsService);
