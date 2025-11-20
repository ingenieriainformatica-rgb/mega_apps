/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";

patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                uuid: { type: String, optional: true },
            },
        },
    },
  });

patch(PosOrder.prototype, {
    async shRemoveOrderline(ev, line) {
        event.stopPropagation()
        var self = this;
        if (this.config.sh_remove_single_item && !this.config.sh_validation_to_remove_single_item) {

            [...self.get_orderlines()].map(async (l) => {
                if (l.uuid == line.uuid) {
                    await self.removeOrderline(l)
                }
            })
        } else {
            const confirmed = await ask(posmodel.dialog, {
                title:  _t("Delete Items"),
                body:_t(
                    'Do you want remove '+line.productName+' ?'
                ),
            });
            if (confirmed) {
                [...self.get_orderlines()].map(async (l) => {
                    if (l.uuid == line.uuid) {
                        await self.removeOrderline(l)
                    }
                })
            }
            

        }
    }
});

patch(PosOrderline.prototype, {
    getDisplayData() {
        return {
            ...super.getDisplayData(),
            uuid: this.uuid
        };
      }
})
