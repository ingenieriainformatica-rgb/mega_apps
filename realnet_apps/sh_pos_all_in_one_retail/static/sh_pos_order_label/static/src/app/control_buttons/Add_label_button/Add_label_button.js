/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { LabelPopup } from "@sh_pos_all_in_one_retail/static/sh_pos_order_label/app/labal_popup/labal_popup"
import { usePos } from "@point_of_sale/app/store/pos_hook";


patch(ControlButtons.prototype, {
  setup() {
    super.setup(...arguments)
    this.dialog = useService("dialog");
    this.pos = usePos();
  },
  async onclickLabelBtn() {
    const lable_product = this.pos.models["product.product"].find((product) => product.default_code == "sh_pos_order_label_line");

    const label = await makeAwaitable(this.dialog, LabelPopup, {
      title: _t("Order Label"),
      'product': lable_product
    });

    const selected_orderline = this.pos.get_order().get_selected_orderline()
    selected_orderline.set_orderline_label(label)

  },
})

