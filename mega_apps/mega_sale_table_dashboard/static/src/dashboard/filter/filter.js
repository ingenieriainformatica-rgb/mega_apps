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
  from.setDate(to.getDate() - 30);
  return { date_from: formatYMD(from), date_to: formatYMD(to) };
}

export class DateFilterBar extends Component {
  static template = "mega_dashboard.DateFilterBar";
  static props = {
    onClickFilter: { type: Function },   // ✅ callback
  };

  setup() {
    this.date_from = useRef('input_date_from');
    this.date_to = useRef('input_date_to');
    
    const def = last30Days();
    this.state = useState({
      date_from: def.date_from,
      date_to: def.date_to,
    });
  }

  onChangeFrom(ev) {
    this.state.date_from = ev.target.value;
  }

  onChangeTo(ev) {
    this.state.date_to = ev.target.value;
  }

  onClickFilter(ev){
      const date_from = this.date_from.el.value
      const date_to = this.date_to.el.value
      this.props.onClickFilter({date_from: date_from, date_to: date_to});
  }

}
