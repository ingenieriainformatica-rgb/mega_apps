/** @odoo-module */

import { CashMovePopup } from "@point_of_sale/app/navbar/cash_move_popup/cash_move_popup";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { serializeDateTime } from "@web/core/l10n/dates";

patch(CashMovePopup.prototype, {
  setup() {
    super.setup(...arguments);
    this.pos = usePos();
    this.orm = useService("orm");
  },
  async confirm() {
    super.confirm();
    var self = this;
    var type = this.state.type;
    var reason = this.state.reason.trim();
    var amount = parseFloat(this.state.amount);
    let sh_date = serializeDateTime(luxon.DateTime.now());
    await this.orm.call("sh.cash.in.out", "try_cash_in_out", [
      this.pos.session.id,
      type,
      amount,
      reason,
      sh_date
  ]);
    if(type == 'in'){
      type = 'cash_in'
    }else{
      type = "cash_out"
    }

    var date_obj = new Date();
    var date =
      date_obj.getFullYear() +
      "-" +
      ("0" + (date_obj.getMonth() + 1)).slice(-2) +
      "-" +
      ("0" + date_obj.getDate()).slice(-2) +
      " " +
      ("0" + date_obj.getHours()).slice(-2) +
      ":" +
      ("0" + date_obj.getMinutes()).slice(-2) +
      ":" +
      ("0" + date_obj.getSeconds()).slice(-2);

    var data = {
      sh_transaction_type: self.pos.cash_in_out_options,
      sh_amount: parseFloat(amount),
      sh_reason: reason,
      sh_session: self.pos.session.id,
      sh_date: date,
    };

    if (type == "in") {
      data["sh_transaction_type"] = "cash_in";
    } else {
      data["sh_transaction_type"] = "cash_out";
      amount = -amount;
    }


  },
});
