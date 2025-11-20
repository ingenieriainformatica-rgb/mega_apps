/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class PriceListPopupWidget extends Component {
    static template = "sh_pos_line_pricelist.PriceListPopupWidget";
    static components = { Dialog };

    setup(){
        super.setup()
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.min_price_pricelist = this.props.min_price_pricelist
        this.pricelist_item_by_id = this.pos.models['product.pricelist.item'].getAllBy('id')
        this.pricelist_by_id = this.pos.models['product.pricelist'].getAllBy('id')
    }
    async onClickPricelistRow(pricelist) {
        var self = this;
        var line = self.pos.get_order().get_selected_orderline();
        let price = pricelist.display_price
        if(line){
            if (self.pos.config.sh_min_pricelist_value) {
                var min_price = line.product_id.get_price(
                    self.min_price_pricelist,
                    1,
                    line.get_price_extra()
                )
                if(price < min_price){
                    this.dialog.add(AlertDialog, {
                        title: _t("Price Warning"),
                        body: _t("PRICE IS BELOW MINIMUM"),
                    });
                    return false
                }
                // if (self.min_price_pricelist.product_id && self.min_price_pricelist.product_id == "All Products" && price < self.min_price_pricelist.display_price && line.is_added) {
                //     this.dialog.add(AlertDialog, {
                //         title: _t("Price Warning"),
                //         body: _t("PRICE IS BELOW MINIMUM"),
                //     });
                // } else if (self.min_price_pricelist.product_id && self.min_price_pricelist.product_id == line.product_id.id && price < self.min_price_pricelist.display_price && line.is_added) {
                //     this.dialog.add(AlertDialog, {
                //         title: _t("Price Warning"),
                //         body: _t("PRICE IS BELOW MINIMUM"),
                //     });
                // } else {
                    var pricelist_data = self.pricelist_by_id[pricelist.id];
                    pricelist_data["items"] = [];
                    for(let each_item of pricelist_data.item_ids){
                        var item_data = self.pricelist_item_by_id[each_item.id];
                        pricelist_data["items"].push(item_data);
                    };
                    line.set_pricelist(pricelist_data);
                    line.set_unit_price(price);
                    self.close()
                // }
            }
            else {
                var pricelist_data = self.pricelist_by_id[pricelist.id];
                pricelist_data["items"] = [];
                for(let each_item of pricelist_data.item_ids){
                    var item_data = self.pricelist_item_by_id[each_item];
                    pricelist_data["items"].push(item_data);
                };
                line.set_pricelist(pricelist_data);
                line.set_unit_price(price);
                self.close()
            }
        }else{
            this.dialog.add(AlertDialog, {
                title: _t("Orderline Not Found"),
                body: _t("Please, Select Orderline!"),
            });
        }
    }
    close() {
        this.props.close();
    }
}