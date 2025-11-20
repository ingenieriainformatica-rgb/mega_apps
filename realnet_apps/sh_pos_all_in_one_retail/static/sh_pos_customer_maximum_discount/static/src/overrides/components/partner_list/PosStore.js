/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);

    },
    async pay() {
        
        if(this.get_order().get_partner() && this.get_order().get_partner().sh_enable_max_dic && this.get_order().get_partner().sh_maximum_discount && this.config.sh_pos_enable_customer_max_discount){

            const currentOrder = this.get_order();
            const selectedOrderLine = currentOrder.get_selected_orderline();
            const currentPartner = currentOrder.get_partner();
    
    
            var sh_total_after_dic = currentOrder.get_total_with_tax()
            var sh_product_total = currentOrder.get_total_without_tax() + currentOrder.get_total_discount()
            var sh_customer_discount_per = ((sh_product_total - sh_total_after_dic) * 100) / sh_product_total
            var sh_customer_max_dis = currentPartner.sh_maximum_discount
    
            if (currentPartner.sh_discount_type == "percentage") {
                var sh_customer_discount_per = ((sh_product_total - sh_total_after_dic) * 100) / sh_product_total
                
                // if(sh_customer_max_dis < selectedOrderLine.discount){
                //     var body = "Sorry, " + sh_customer_discount_per.toFixed(2) + "% discount is not allowed. Maximum discount for this customer is " + sh_customer_max_dis + "%";
                //     this.dialog.add(AlertDialog, {
                //         title: 'Exceed Discount Limit !',
                //         body: body,
                //     })
    
                // }
    
    
                if (sh_customer_discount_per > sh_customer_max_dis) {
    
                    var body = "Sorry, " + sh_customer_discount_per.toFixed(2) + "% discount is not allowed. Maximum discount for this customer is " + sh_customer_max_dis + "%";
                    this.dialog.add(AlertDialog, {
                        title: 'Exceed Discount Limit !',
                        body: body,
                        confirm: () => {
                            // selectedOrderLine.set_discount(0)
                            currentOrder.set_partner(false);
                            
    
    
                        },
                    })
                }else{
                    await super.pay();
                }
               
                // if (currentPartner?.sh_maximum_discount) {
                //     selectedOrderLine.set_discount(currentPartner?.sh_maximum_discount)
    
    
                // }
            }
    
            else if(currentPartner.sh_discount_type == "fixed") {
                var sh_customer_discount_fixed = currentOrder.get_total_discount()
    
    
    
                if (sh_customer_discount_fixed > sh_customer_max_dis) {
    
                    var body = "Sorry, " + sh_customer_discount_fixed.toFixed(2) + " discount is not allowed. Maximum discount for this customer is " + sh_customer_max_dis;
                    this.dialog.add(AlertDialog, {
                        title: 'Exceed Discount Limit !',
                        body: body,
                        confirm: () => {
                            // selectedOrderLine.set_discount(0)
                            currentOrder.set_partner(false);
                            
    
    
                        },
                    })
                }else{
                    await super.pay();
                }
            }
            
    
            else {
                await super.pay();
            }
        }else{
            await super.pay();
        }
    },
    async selectPartner(partner) {
        const res = await super.selectPartner(partner);
        
        console.log("***** &&& ",this.get_order().get_partner())
        
        if(this.get_order().get_partner() && this.get_order().get_partner().sh_enable_max_dic && this.get_order().get_partner().sh_maximum_discount && this.config.sh_pos_enable_customer_max_discount){

            const currentOrder = this.get_order();
            const selectedOrderLine = currentOrder.get_selected_orderline();
            const currentPartner = currentOrder.get_partner();
    
    
            var sh_total_after_dic = currentOrder.get_total_with_tax()
            var sh_product_total = currentOrder.get_total_without_tax() + currentOrder.get_total_discount()
            var sh_customer_discount_per = ((sh_product_total - sh_total_after_dic) * 100) / sh_product_total
            var sh_customer_max_dis = currentPartner.sh_maximum_discount
    
            if (currentPartner.sh_discount_type == "percentage") {
                var sh_customer_discount_per = ((sh_product_total - sh_total_after_dic) * 100) / sh_product_total
                
                // if(sh_customer_max_dis < selectedOrderLine.discount){
                //     var body = "Sorry, " + sh_customer_discount_per.toFixed(2) + "% discount is not allowed. Maximum discount for this customer is " + sh_customer_max_dis + "%";
                //     this.dialog.add(AlertDialog, {
                //         title: 'Exceed Discount Limit !',
                //         body: body,
                //     })
    
                // }
    
    
                if (sh_customer_discount_per > sh_customer_max_dis) {
    
                    var body = "Sorry, " + sh_customer_discount_per.toFixed(2) + "% discount is not allowed. Maximum discount for this customer is " + sh_customer_max_dis + "%";
                    this.dialog.add(AlertDialog, {
                        title: 'Exceed Discount Limit !',
                        body: body,
                        confirm: () => {
                            // selectedOrderLine.set_discount(0)
                            currentOrder.set_partner(false);
                            
    
    
                        },
                    })
                } 
               
                // if (currentPartner?.sh_maximum_discount) {
                //     selectedOrderLine.set_discount(currentPartner?.sh_maximum_discount)
    
    
                // }
            }
    
            else if(currentPartner.sh_discount_type == "fixed") {
                var sh_customer_discount_fixed = currentOrder.get_total_discount()
    
    
    
                if (sh_customer_discount_fixed > sh_customer_max_dis) {
    
                    var body = "Sorry, " + sh_customer_discount_fixed.toFixed(2) + " discount is not allowed. Maximum discount for this customer is " + sh_customer_max_dis;
                    this.dialog.add(AlertDialog, {
                        title: 'Exceed Discount Limit !',
                        body: body,
                        confirm: () => {
                            // selectedOrderLine.set_discount(0)
                            currentOrder.set_partner(false);
                            
    
    
                        },
                    })
                }
                return res;
            }
            
    
            else {
                return super.confirm()
            }
        }

    }

});

