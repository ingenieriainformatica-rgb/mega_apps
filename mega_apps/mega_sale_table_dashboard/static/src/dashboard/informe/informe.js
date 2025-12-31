/** @odoo-module */

import { Component } from "@odoo/owl";

export class Informe extends Component {
  static template = "mega_dashboard.KpiCards";
  static props = { data: Array, grand: Object};

  get warehouses() {
    const blacklist = ["GRUPOMEGA"]; // 👈 aquí pones las sedes que NO quieres
    return (this.props.data || []).filter((wh) => {
      const name = (wh.warehouse_name || "").trim().toUpperCase();
      return !blacklist.includes(name);
    });
  }

  get grand() {
    return this.props.grand || { total_sales: 0, count_orders: 0 };
  }

}
