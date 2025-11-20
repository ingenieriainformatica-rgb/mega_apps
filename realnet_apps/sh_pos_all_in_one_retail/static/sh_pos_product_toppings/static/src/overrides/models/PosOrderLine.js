/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { formatCurrency  } from "@web/core/currency";

patch(PosOrderline.prototype, {
    sh_topping_merge_with(orderline){
        if (this.config.sh_enable_toppings && this.config.sh_allow_same_product_different_qty) {
            if (this.sh_is_has_topping) {
                return false
            }
        }
        if ((this.sh_is_topping && orderline.sh_is_topping)) {
            if (this.sh_base_line_id.id == orderline.sh_base_line_id.id) {
                return true
            } else {
                return false
            }
        }
        if (this.sh_is_topping) {
            return false
        }
    },
    set_has_topping(has_topping){
        this.sh_is_has_topping =  has_topping
    },
    can_be_merged_with(orderline) {
        if ((this.config.sh_enable_toppings && this.config.sh_allow_same_product_different_qty) || (this.sh_is_topping && orderline.sh_is_topping) || this.sh_is_topping) {
            return (
                this.sh_topping_merge_with(orderline) &&
                super.can_be_merged_with(...arguments)
            );
        }else{
            return (
                super.can_be_merged_with(...arguments)
            );
        }
        
    },
    isPartOftopping() {        
        return Boolean(this.sh_base_line_id || this.sh_topping_line_ids?.length);
    },
    getDisplayData() {
        
        var topping_line = []
        if(this.sh_is_has_topping){
            for (let each_topping of this.sh_topping_line_ids) {
                topping_line.push({

                    productName: each_topping.get_full_product_name(),
                    price: each_topping.getPriceString(),
                    qty: each_topping.get_quantity_str(),
                    unit: each_topping.product_id.uom_id ? each_topping.product_id.uom_id.name : "",
                    unitPrice: formatCurrency(each_topping.get_unit_display_price(), each_topping.currency),
                    oldUnitPrice: each_topping.get_old_unit_display_price()
                        ? formatCurrency(each_topping.get_old_unit_display_price(), each_topping.currency)
                        : "",
                    discount: each_topping.get_discount_str(),
                    customerNote: each_topping.get_customer_note() || "",
                    internalNote: each_topping.getNote(),
                    comboParent: each_topping.combo_parent_id?.get_full_product_name?.() || "",
                    packLotLines: each_topping.pack_lot_ids.map(
                        (l) =>
                            `${l.pos_order_line_id.product_id.tracking == "lot" ? "Lot Number" : "SN"} ${
                                l.lot_name
                            }`
                    ),
                    price_without_discount: formatCurrency(
                        each_topping.getUnitDisplayPriceBeforeDiscount(),
                        each_topping.currency
                    ),
                    taxGroupLabels: [
                        ...new Set(
                            each_topping.product_id.taxes_id
                                ?.map((tax) => tax.tax_group_id.pos_receipt_label)
                                .filter((label) => label)
                        ),
                    ].join(" "),

                })
            }
        }
        return {
            ...super.getDisplayData(),
            sh_is_topping: this.sh_is_topping,
            sh_is_has_topping: this.sh_is_has_topping,
            sh_base_line_id: this.sh_base_line_id ? this.sh_base_line_id.id: false,
            id: this.id,
            sh_topping_line_ids: this.sh_is_has_topping ? topping_line: false,
        };
    },
    getDisplayClasses() {
        return {
            ...super.getDisplayClasses(),
            "sh-is-topping": this.sh_base_line_id ? this.sh_base_line_id : false,
        };
    },
});



patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                sh_is_topping: { type: Boolean, optional: true },
                sh_is_has_topping: { type: Boolean, optional: true },
                sh_base_line_id: { type:  [Boolean, String, Number], optional: true },
                id: { type: [String, Number], optional: true },
                sh_is_show_orderline_icon : {type : Boolean , optional: true},
                sh_topping_line_ids: { type:  [Boolean, String, Number, Object], optional: true },
            },
        },
    },
});
