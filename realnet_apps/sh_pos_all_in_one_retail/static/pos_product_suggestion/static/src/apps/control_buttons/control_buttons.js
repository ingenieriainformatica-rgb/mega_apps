/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeAwaitable, ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";

patch(ControlButtons.prototype, {
//   UOM feature code

    async changeUom() {
        var self = this
        let selected_orderline = self.pos.get_order()?.get_selected_orderline()
        if(selected_orderline){
            let product_id = selected_orderline.product_id
            if(product_id && product_id.sh_uom_line_ids && product_id.sh_uom_line_ids.length){
                let uom_ids = product_id.sh_uom_line_ids
                let uom_list = uom_ids.map((uom) => {
                    return {
                        id: uom.id,
                        item: uom,
                        label: uom.uom_name,
                        isSelected: false,
                    };
                })
                const payload = await makeAwaitable(self.dialog, SelectionPopup, {
                    title: _t("Select the UOM"),
                    list: uom_list,
                });
                if (payload) {
                    
                    const priceList = self.pos.getDefaultPricelist();
                    if(priceList){
                        let pricelistRule = selected_orderline.product_id.getPricelistRule(priceList , selected_orderline.get_quantity())
                        if(pricelistRule && pricelistRule.sh_uom_id && pricelistRule.sh_uom_id == payload.uom_id){
                            selected_orderline.set_custom_uom(pricelistRule.sh_uom_id)
                            selected_orderline.set_unit_price(pricelistRule.fixed_price)
                        }else{
                            if(payload.sh_qty > 0){
                                selected_orderline.set_quantity(payload.sh_qty)
                            }
                            selected_orderline.set_custom_uom(payload)
                            selected_orderline.set_unit_price(payload.price)
                        }
                        
                        
                    }else{
                        if(payload.sh_qty > 0){
                            selected_orderline.set_quantity(payload.sh_qty)
                        }
                        selected_orderline.set_custom_uom(payload)
                        selected_orderline.set_unit_price(payload.price)
                    }
                }   
            }
            
        }else{
            this.dialog.add(AlertDialog, {
                title: _t("Orderline Not Found!"),
                body: _t("Please Select Orderline."),
            });
        }
    },
});
