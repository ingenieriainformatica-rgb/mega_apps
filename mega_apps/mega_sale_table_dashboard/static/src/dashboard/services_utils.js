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

function getLast30DaysRange() {
  const today = new Date();
  const from = new Date(today);
  from.setDate(today.getDate() - 30);

  return {
    date_from: formatYMD(from),
    date_to: formatYMD(today),
  };
}

const statisticsService = {
  start() {
    const statistics = reactive({ isReady: false, date_from: null, date_to: null });

    const loadDataLottery = async () => {
      try {
        const { date_from, date_to } = getLast30DaysRange();

        const updates = await rpc("/sales/statistics", {
          date_from,
          date_to,
        });

        Object.assign(statistics, updates, {
          isReady: true,
          date_from,
          date_to,
        });
      } catch (e) {
        console.error("sales.statistics loadData error:", e);
      }
    };

    loadDataLottery();
    setInterval(loadDataLottery, 60 * 1000);

    return statistics;
  },
};

registry.category("services").add("sales.statistics", statisticsService);
