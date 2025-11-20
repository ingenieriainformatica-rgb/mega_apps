/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PriceListPopupWidget } from "@sh_pos_all_in_one_retail/static/sh_pos_line_pricelist/apps/pricelist_popup/pricelist_popup";
import { formatFloat, roundDecimals, roundPrecision, floatIsZero } from "@web/core/utils/numbers";

patch(PosOrderline.prototype, {
    getDisplayData() {
        return {
            ...super.getDisplayData(),
            productId :  this.get_product() ? this.get_product().id :false
        };
    },
    set_pricelist(pricelist) {
        this.pricelist = pricelist;
    },
    get_pricelist() {
        return this.pricelist || false;
    },
    get_lst_price() {
        if(this.get_pricelist()){
            return this.product_id.get_price(this.get_pricelist(), 1, this.price_extra);
        }else{
            return super.get_lst_price()
        }
    },
    set_quantity(quantity, keep_price) {
        var res = super.set_quantity(quantity, keep_price)
        if(this.get_pricelist()){
            this.set_unit_price(
                this.product_id.get_price(
                    this.get_pricelist(),
                    this.get_quantity(),
                    this.get_price_extra()
                )
            );
        }
        return res
    },
    set_unit_price(price) {
        var self = this;
        if (self.config.sh_min_pricelist_value) {
            var min_price = self.product_id.get_price(
                self.config.sh_min_pricelist_value,
                1,
                self.get_price_extra()
            )
            if(price < min_price){
                alert("PRICE IS BELOW MINIMUM")
                return false
            }
        }
        var res = super.set_unit_price(price)
        return res
    }
});

patch(PosOrder.prototype, {
    async on_click_pricelist_icon(line) {
        event.stopPropagation()
        line.available_pricelist = [];
        line.pricelist_for_code = [];
        line.min_price_pricelist;
        var self = line;
        let pricelist_item_by_id = await posmodel.models['product.pricelist.item'].getAllBy('id')
        let product = await posmodel.models['product.product'].getAll().find((product) => product.id === line.productId)
        for (var k = 0; k < posmodel.models['product.pricelist'].getAll().length; k++) {
            var each_pricelist = await posmodel.models['product.pricelist'].getAll()[k]
            
            if (posmodel.config.sh_min_pricelist_value && (each_pricelist.id == posmodel.config.sh_min_pricelist_value.id)) {
                let price;
                each_pricelist["items"] = [];
                
                for (var i = 0; i < each_pricelist.item_ids.length; i++) {
                    var each_item = each_pricelist.item_ids[i]
                    
                    var item_data = pricelist_item_by_id[each_item.id];
                    if (item_data.product_id && item_data.product_id.id == line.productId) {
                        each_pricelist["items"].push(item_data);
                        each_pricelist["product_id"] = line.productId;
                    }
                    if (item_data.display_name == "All Products") {
                        each_pricelist["items"].push(item_data);
                        each_pricelist["product_id"] = "All Products";
                    }
                }
                price = await product.get_price(each_pricelist, line.qty);
                each_pricelist["display_price"] = price;
                line.min_price_pricelist = each_pricelist;
            }
            
            if (posmodel.config.sh_pricelist_for_code && (each_pricelist.id == posmodel.config.sh_pricelist_for_code.id)) {
                let price;
                each_pricelist["items"] = [];
                for (var j = 0; j < each_pricelist.item_ids.length; j++) {
                    var each_item = each_pricelist.item_ids[j]
                   
                    var item_data = pricelist_item_by_id[each_item.id];
                    
                    each_pricelist["items"].push(item_data);
                }
                
                price = await product.get_price(each_pricelist, line.qty);
                var sNumber = price.toString(); 
                var code = "";
                for(var each_number of sNumber){
                    if (each_number == "1") {
                        code += "L";
                    }
                    if (each_number == "2") {
                        code += "U";
                    }
                    if (each_number == "3") {
                        code += "C";
                    }
                    if (each_number == "4") {
                        code += "K";
                    }
                    if (each_number == "5") {
                        code += "Y";
                    }
                    if (each_number == "6") {
                        code += "H";
                    }
                    if (each_number == "7") {
                        code += "O";
                    }
                    if (each_number == "8") {
                        code += "R";
                    }
                    if (each_number == "9") {
                        code += "S";
                    }
                    if (each_number == "0") {
                        code += "E";
                    }
                    if (each_number == ".") {
                        code += ".";
                    }
                };
                each_pricelist["display_price"] = code;
                line.pricelist_for_code.push(each_pricelist);
            }
            else {                
                for (const key in posmodel.config.available_pricelist_ids) {
                    if (posmodel.config.available_pricelist_ids[key].id === each_pricelist.id) {                        
                        let price;
                        each_pricelist["items"] = [];
                        for (var j = 0; j < each_pricelist.item_ids.length; j++) {
                            var each_item = each_pricelist.item_ids[j];
                            var item_data = pricelist_item_by_id[each_item];
                            each_pricelist["items"].push(item_data);
                        }
                        price = await product.get_price(each_pricelist, line.qty);
                        each_pricelist["display_price"] = price;
                        line.available_pricelist.push(each_pricelist);
                    }
                }
            }
        }      
        posmodel.env.services.dialog.add(PriceListPopupWidget, {
            title: _t("PRICELIST"),
            'available_pricelist': line.available_pricelist,
            'pricelist_for_code': line.pricelist_for_code,
            'min_price_pricelist': line.min_price_pricelist,
        });
    }
})