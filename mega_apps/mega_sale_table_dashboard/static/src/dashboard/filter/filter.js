/** @odoo-module */

import { Component, useState } from "@odoo/owl";

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
    onClickFilter: {
        type: Object
    }
  };

  setup() {
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

  async onApply() {
    // validación básica
    if (this.state.date_from && this.state.date_to && this.state.date_from > this.state.date_to) {
      // si ya tienes notification service, aquí lo usas
      alert("La fecha 'Desde' no puede ser mayor que 'Hasta'.");
      return;
    }
    await this.props.onApplyRange({
      date_from: this.state.date_from,
      date_to: this.state.date_to,
    });
  }

  async onReset() {
    const def = last30Days();
    this.state.date_from = def.date_from;
    this.state.date_to = def.date_to;
    await this.props.onApplyRange(def);
  }

  onClickFilter(ev){
      console.log("Filter clicked",this.state.date_from ,this.state.date_to);
      this.props.onClickFilter();
  }

}
