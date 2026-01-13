/** @odoo-module */

import { Component, useState, useRef } from "@odoo/owl";


function formatYMD(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}

function last30Days() {
  const to = new Date();
  const from = new Date(to);
  from.setDate(to.getDate() - 7);
  return { date_from: formatYMD(from), date_to: formatYMD(to) };
}

export class DateFilterBar extends Component {
  static template = "mega_dashboard.DateFilterBar";
  static props = {
    onChangeWarehouse: { type: Function, optional: true },
    onClickFilter: { type: Function },
    warehouses: { type: Array, optional: true },
    loadingWarehouses: { type: Boolean, optional: true },
    journals: { type: Array, optional: true },
    loadingJournals: { type: Boolean, optional: true },
  };

  setup() {
    this.date_from = useRef('input_date_from');
    this.date_to = useRef('input_date_to');
    this.warehouse_id = useRef('input_warehouse_id');
    this.journal_id = useRef('input_journal_id');

    const def = last30Days();

    this.state = useState({
      date_from: def.date_from,
      date_to: def.date_to,
      warehouse_id: this.warehouse_id.el ? this.warehouse_id.el.value : null,
    });

  }

  onClickFilter(ev){
      const warehouse_id = this.warehouse_id.el.value;
      const date_from = this.date_from.el.value
      const date_to = this.date_to.el.value
      const journal = this.journal_id.el.value
      this.props.onClickFilter({warehouse_id: warehouse_id, date_from: date_from, date_to: date_to, journal: journal});
  }

  onChangeWarehouse(ev) {
    const warehouse_id = ev.target.value || "";

    if (this.props.onChangeWarehouse) {
      this.props.onChangeWarehouse(warehouse_id);
    }
  }

}
