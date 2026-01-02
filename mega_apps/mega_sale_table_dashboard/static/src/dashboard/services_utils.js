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

// Default: últimos 30 días (puedes cambiar a inicio de mes)
function getDefaultRange() {
  const today = new Date();
  const from = new Date(today);
  from.setDate(today.getDate() - 30);
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

const statisticsService = {
  start() {
    const def = getDefaultRange();

    const statistics = reactive({
      isReady: false,
      date_from: def.date_from,
      date_to: def.date_to,

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

          // Persistimos el rango normalizado
          this.date_from = date_from;
          this.date_to = date_to;

          const updates = await rpc("/sales/statistics", { date_from, date_to });

          Object.assign(this, updates, {
            isReady: true,
          });
        } catch (e) {
          console.error("sales.statistics reload error:", e);
        }
      },

      // ✅ ESTE ES EL QUE TE FALTA
      async setRange({ date_from, date_to }) {
        const norm = normalizeRange({ date_from, date_to });
        this.date_from = norm.date_from;
        this.date_to = norm.date_to;
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
