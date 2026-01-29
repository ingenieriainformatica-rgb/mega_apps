/** @odoo-module */

import { Component } from "@odoo/owl";

export class Advisor extends Component {
  static template = "mega_dashboard.Advisor";
  static props = { data: Array };

   get rows() {
     return this.props.data || [];
   }

}
