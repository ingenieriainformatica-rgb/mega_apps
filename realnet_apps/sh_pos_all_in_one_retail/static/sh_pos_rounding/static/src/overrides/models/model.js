/** @odoo-module **/

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { _t } from "@web/core/l10n/translation";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { omit } from "@web/core/utils/objects";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";


patch(PosOrderline.prototype, {
    getDisplayData() {
        return {
            ...super.getDisplayData(),
            sh_hide_orderline: this.product_id.is_rounding_product ? true : false,

        };
    },
    getDisplayClasses() {
        return {
            ...super.getDisplayClasses(),
            "sh_hide_orderline": this.product_id.is_rounding_product
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
                sh_hide_orderline: { type: Boolean, optional: true },
            },
        },
    },
});


patch(PosOrder.prototype, {
    setup() {
        this.is_payment_round = true
        this.total_rounding  =  0.0
        this.validate_order = false
        super.setup(...arguments);
    }, 
    get_rounding_total(order_total) {
        var total_with_tax = order_total;
        var round_total = total_with_tax;
        if (this.config.rounding_type == "fifty") {
            var division_by_50 = total_with_tax / 50;
            var floor_value = Math.floor(division_by_50);
            var ceil_value = Math.ceil(division_by_50);
            if (floor_value % 2 != 0) {
                round_total = floor_value * 50;
                this.round_total = round_total
            }
            if (ceil_value % 2 != 0) {
                round_total = ceil_value * 50;
            }
            const rounding_price = round_total - order_total;
            this.set_rounding_price(rounding_price)
        } else {
            round_total = Math.round(total_with_tax);
            const rounding_price = round_total - order_total;
            this.set_rounding_price(rounding_price)
        }

        return  round_total;
    },

    get_total_with_tax() {        
        if(this.config.sh_enable_rounding && this.get_is_payment_round() && !this.validate_order){
            return this.get_rounding_total(this.get_total_without_tax() + this.get_total_tax());
        }else{
            return super.get_total_with_tax()
        }
    },
    get_round_total_with_tax() {
        let round_total_with_tax = this.get_rounding_total(this.get_total_without_tax() + this.get_total_tax());
        var rounding_price = round_total_with_tax - this.get_total_with_tax();
        this.set_rounding_price(rounding_price)
        return round_total_with_tax
    },
    set_rounding_price(price) {
        this.total_rounding = price
    },
    get_rounding_amount(){
        return  this.total_rounding
    },
    set_validate_oreder(para){
        this.validate_order = para
    },
    get_is_payment_round() {
        return this.is_payment_round || false;
    },
    set_is_payment_round(is_payment_round) {
        this.is_payment_round = is_payment_round;
    },  
    export_for_printing() {
        var receipt = super.export_for_printing(...arguments);
        receipt["rounding_amount"] = this.get_rounding_amount();
        return receipt;
    }
});