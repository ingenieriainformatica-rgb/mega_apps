/** @odoo-module */

import { Chrome } from "@point_of_sale/app/pos_app";
import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";

patch(Chrome.prototype, {
     setup() {
         super.setup(...arguments)
document.addEventListener("keydown", (event) => {
    if(self && self.posmodel && self.posmodel.keysPressed){
        self.posmodel.keysPressed[event.key] = true;
    }
});

document.addEventListener("keyup", (event) => {
    if(self && self.posmodel && self.posmodel.keysPressed){
        delete self.posmodel.keysPressed[event.key];
    }
});

document.addEventListener("keydown", async(event) => {
    if (self && self.posmodel && self.posmodel.config && self.posmodel.config.sh_enable_shortcut &&  self.posmodel.keysPressed) {
        self.posmodel.keysPressed[event.key] = true;
        self.posmodel.pressedKeyList = [];
        
        for (var key in self.posmodel.keysPressed) {
            console.log("key ", key);
            
            if (self.posmodel.keysPressed[key]) {
                self.posmodel.pressedKeyList.push(key);
            }
        }
        if (self.posmodel.pressedKeyList.length > 0) {
            var pressed_key = "";
            for (var i = 0; i < self.posmodel.pressedKeyList.length > 0; i++) {
                if (self.posmodel.pressedKeyList[i]) {
                    if (pressed_key != "") {
                        pressed_key = pressed_key + "+" + self.posmodel.pressedKeyList[i];
                    } else {
                        pressed_key = self.posmodel.pressedKeyList[i];
                    }
                }
            };

            if ($(".payment-screen").is(":visible")) {
                if (self.posmodel.screen_by_key[pressed_key]) {
                    event.preventDefault();
                    if (self.posmodel.screen_by_key[pressed_key]) {
                        var payment_methods = self.posmodel.models["pos.payment.method"].getAllBy("id");
                        if(payment_methods){
                            let payment_method = payment_methods[self.posmodel.screen_by_key[pressed_key]]
                            if (payment_method) {
                                self.posmodel.get_order().add_paymentline(payment_method);
                            }
                        }
                    }
                }
            }
            
            for (var key in self.posmodel.key_screen_by_id) {
                if (self.posmodel.key_screen_by_id[key] == pressed_key) {
                    if (!$(".border-0 mx-2").is(":focus") && !$('textarea').is(":focus") && $('input:focus').length <= 0) {
                        if (key == "select_up_orderline") {
                            event.preventDefault();
                            event.stopPropagation();
                            if ($(".product-screen").is(":visible")) {
                                $(document).find("div.product-screen .order-container li.selected").prev("li.orderline").trigger("click");
                            }
                        } else if (key == "select_down_orderline") {
                            event.preventDefault();
                            event.stopPropagation();
                            if ($(".product-screen").is(":visible")) {
                                $(document).find("div.product-screen .order-container li.selected").next("li.orderline").trigger("click");
                            }
                        } else if (key == "select_up_customer") {
                            console.log("======called =====");
                            
                            if ($(document).find("table.partner-info tr.selected").length > 0) {
                                $(document).find("table.partner-info tr.selected").prev("tr.partner-line").click();
                            } else {
                                var clientLineLength = $(document).find(".partner-info").length;
                                console.log("clientLineLength", clientLineLength);
                                
                                if (clientLineLength > 0) {
                                    $($(document).find(".partner-info")[clientLineLength - 1]).click();
                                }
                            }
                        } else if (key == "select_down_customer") {
                            if ($(document).find("table.partner-info tr.selected").length > 0) {
                                $(document).find("table.partner-info tr.selected").next("tr.partner-line").click();
                            } else {
                                var clientLineLength = $(document).find("table.partner-list tbody.partner-list-contents tr.partner-line").length;
                                if (clientLineLength > 0) {
                                    $($(document).find("table.partner-list tbody.partner-list-contents tr.partner-line")[0]).click();
                                }
                            }
                        } else if (key == "go_payment_screen") {                            
                            event.preventDefault();
                            event.stopPropagation();
                            if ($(".product-screen").is(":visible")) {
                               await self.posmodel.showScreen("PaymentScreen")
                                self.posmodel.keysPressed = {};
                               await self.posmodel.get_order().clean_empty_paymentlines()
                            }
                        } else if (key == "go_customer_Screen") {
                            event.preventDefault();
                            event.stopPropagation();
                            if ($(".product-screen").is(":visible")) {                                
                                self.posmodel.selectPartner()
                            }
                            if ($(".payment-screen").is(":visible")) {
                                self.posmodel.selectPartner()
                            }
                        } else if (key == "validate_order") {
                            event.preventDefault();
                            event.stopPropagation();
                            if ($(".payment-screen").is(":visible")) {
                                if ($(".next").hasClass("highlight")) {
                                    $(".next.highlight").trigger("click");
                                }
                            }
                        } else if (key == "next_order") {
                            event.preventDefault();
                            event.stopPropagation();
                            if ($(".receipt-screen").is(":visible")) {
                                if ($(".next").hasClass("highlight")) {
                                    $(".next.highlight").trigger("click");
                                }
                            }
                        } else if (key == "go_to_previous_screen") {
                            event.preventDefault();
                            event.stopPropagation();
                            if (!$(".product-screen").is(":visible") && !$(".receipt-screen").is(":visible") && !$(".ticket-screen").is(":visible")) {
                                $(".back").trigger("click");
                            }
                            if ($(".ticket-screen").is(":visible")) {
                                $(".discard").trigger("click");
                            }
                        } else if (key == "select_quantity_mode") {
                            if ($(".product-screen").is(":visible")) {
                                let btn = $("button.numpad-button:contains('Qty')")                                
                                btn.click();
                            }
                        } else if (key == "select_discount_mode") {
                            if ($(".product-screen").is(":visible")) {
                                let btn = $("button.numpad-button:contains('%')")
                                btn.click();
                            }
                        } else if (key == "select_price_mode") {
                            if ($(".product-screen").is(":visible")) {
                                let btn = $("button.numpad-button:contains('Price')")
                                btn.click();
                            }
                        } else if (key == "search_product") {
                            event.preventDefault();
                            event.stopPropagation();
                            if ($(".product-screen").is(":visible")) {
                                var inputElement = $('input:input[placeholder="Search products..."]');
                                inputElement.focus();
                                // $(".search-clear-partner").click();
                            }
                        } else if (key == "add_new_order") {
                            event.preventDefault();
                            event.stopPropagation();
                            if ($(".ticket-screen").is(":visible")) {
                                self.posmodel.add_new_order()
                                self.posmodel.showScreen("ProductScreen");
                            }
                        } else if (key == "destroy_current_order") {
                            event.preventDefault();
                            event.stopPropagation();
                            $(document).find("div.ticket-screen div.orders div.order-row.highlight div.delete-button").click();
                        } else if (key == "delete_orderline") {
                            if ($(".product-screen").is(":visible")) {
                                if (self.posmodel.get_order().get_selected_orderline()) {
                                    // setTimeout(function () {
                                    self.posmodel.get_order().removeOrderline(self.posmodel.get_order().get_selected_orderline());
                                    // }, 150);
                                }
                            }
                        } else if (key == "search_customer") {
                            event.preventDefault();
                            event.stopPropagation();
                            if ($(".partner-list").is(":visible")) {
                                $("input.border-0.mx-2").focus();
                            }
                        } else if (key == "set_customer") {
                            event.preventDefault();
                            event.stopPropagation();
                            if ($(".partnerlist-screen").is(":visible")) {
                                if ($(document).find("table.partner-list tbody.partner-list-contents tr.partner-line.highlight")) {
                                    $(document).find("table.partner-list tbody.partner-list-contents tr.partner-line.highlight").click();
                                }
                            }
                        } else if (key == "create_customer") {
                            event.preventDefault();
                            event.stopPropagation();
                            if ($(".partner-list").is(":visible")) {
                               self.posmodel.editPartner()
                            }
                        } else if (key == "save_customer") {
                            // if (!$(document.activeElement).is(":focus")) {
                                event.preventDefault();
                                event.stopPropagation();
                                if ($(".partner-list").is(":visible")) {
                                    let btn =  $(".btn.o_form_button_save")
                                    btn.click();
                                }
                            // }
                        } else if (key == "edit_customer") {
                                event.preventDefault();
                                event.stopPropagation();
                                if ($(".partner-list").is(":visible")) {
                                    if(self && self.posmodel && self.posmodel.get_order() && self.posmodel.get_order().get_partner()){
                                        self.posmodel.editPartner(self.posmodel.get_order().get_partner())
                                    }else{
                                        self.posmodel.editPartner()
                                    }
                                  
                                }
                        } else if (key == "select_up_payment_line") {
                            console.log("=======================");
                            
                            if ($(".payment-screen").is(":visible")) {
                                if ($(document).find("div.paymentline.selected").length > 0) {
                                    var highlighted_payment_line = $(document).find("div.paymentline.selected");
                                    if (highlighted_payment_line.prev("div.paymentline").length > 0) {
                                        console.log("=======================+++++++++++++++++", $(document).find("div.paymentline.selected").prev("div.paymentline"));
                                        let new_line = $(document).find("div.paymentline.selected").prev("div.paymentline")
                                        highlighted_payment_line.removeClass("selected");
                                        new_line.addClass("selected");
                                    }
                                } else {
                                    var orderLineLength = $(document).find("div.paymentline.selected").length;
                                    if (orderLineLength > 0) {
                                        $($(document).find("div.paymentline")[orderLineLength - 1]).addClass("selected");
                                    }
                                }
                            }
                        } else if (key == "select_down_payment_line") {
                            if ($(".payment-screen").is(":visible")) {
                                if ($(document).find("div.paymentline.selected").length > 0) {
                                    var highlighted_payment_line = $(document).find("div.paymentline.selected");
                                    if (highlighted_payment_line.next("div.paymentline").length > 0) {
                                        $(document).find("div.paymentline.selected").next("div.paymentline").click();
                                        highlighted_payment_line.removeClass("selected");
                                    }
                                } else {
                                    var orderLineLength = $(document).find("div.paymentline.selected").length;
                                    if (orderLineLength > 0) {
                                        $($(document).find("div.paymentline")[0]).click();
                                    }
                                }
                            }
                        } else if (key == "delete_payment_line") {
                            if ($(".payment-screen").is(":visible")) {
                                setTimeout(function () {
                                    event.preventDefault();
                                    var elem = $(document).find("div.payment-screen  div.left-content div.paymentline.selected");

                                    if (elem.next("div.paymentline").length > 0) {
                                        $(document).find("div.payment-screen  div.left-content div.paymentline.selected button.delete-button").trigger("click");
                                        elem.next("div.paymentline").click();
                                        self.posmodel.keysPressed = {};
                                    } else {
                                        $(document).find("div.payment-screen  div.paymentline.selected button.delete-button").trigger("click");
                                        if (elem.prev("div.paymentline").length > 0) {
                                            elem.prev("div.paymentline").click();
                                            self.posmodel.keysPressed = {};
                                        }
                                    }
                                }, 200);
                            }
                        } else if (key == "+10") {
                            if ($(".payment-screen").is(":visible")) {
                                let btn =  $("button:contains('+10')")
                                btn.click();
                            }
                        console.log("keyyyyyyyy", key);
                        
                        } else if (key == "+20") {
                            if ($(".payment-screen").is(":visible")) {
                                let btn =  $("button:contains('+20')")
                                btn.click();
                            }
                        } else if (key == "+50") {
                            event.preventDefault();
                            event.stopPropagation();
                            if ($(".payment-screen").is(":visible")) {
                                let btn =  $("button:contains('+50')")
                                btn.click();
                            }
                        } else if (key == "go_order_Screen") {
                            if ($(".payment-screen").is(":visible") || $(".product-screen").is(":visible")) {
                                self.posmodel.showScreen("TicketScreen")

                                // let btn =  $("button:contains('Refund')")
                                // btn.click();
                            }
                        } else if (key == "search_order") {
                            event.preventDefault();
                            event.stopPropagation();
                            if ($(".ticket-screen").is(":visible")) {
                                $(".search input").focus();
                            }
                        } else if (key == "select_up_order") {
                            if ($(".ticket-screen").is(":visible")) {
                                if ($(document).find("div.ticket-screen div.orders div.order-row.highlight").length > 0) {
                                    var highlighted_order = $(document).find("div.ticket-screen div.orders div.order-row.highlight");
                                    if (highlighted_order.prev("div.order-row").length > 0) {
                                        $(document).find("div.ticket-screen div.orders div.order-row.highlight").prev("div.order-row").addClass("highlight");
                                        highlighted_order.removeClass("highlight");
                                    }
                                } else {
                                    var orderLineLength = $(document).find("div.ticket-screen div.orders div.order-row").length;
                                    if (orderLineLength > 0) {
                                        $($(document).find("div.ticket-screen div.orders div.order-row")[orderLineLength - 1]).addClass("highlight");
                                    }
                                }
                            }
                        } else if (key == "select_down_order") {
                            if ($(".ticket-screen").is(":visible")) {
                                if ($(document).find("div.ticket-screen div.orders div.order-row.highlight").length > 0) {
                                    var highlighted_order = $(document).find("div.ticket-screen div.orders div.order-row.highlight");
                                    if (highlighted_order.next("div.order-row").length > 0) {
                                        $(document).find("div.ticket-screen div.orders div.order-row.highlight").next("div.order-row").addClass("highlight");
                                        highlighted_order.removeClass("highlight");
                                    }
                                } else {
                                    var orderLineLength = $(document).find("div.ticket-screen div.orders div.order-row").length;
                                    if (orderLineLength > 0) {
                                        $($(document).find("div.ticket-screen div.orders div.order-row")[0]).addClass("highlight");
                                    }
                                }
                            }
                        } else if (key == "select_order") {
                            if ($(".ticket-screen").is(":visible")) {
                                if ($(document).find("div.ticket-screen div.orders div.order-row.highlight").length > 0) {
                                    $(document).find("div.ticket-screen div.orders div.order-row.highlight").click();
                                }
                            }
                        }
                    }
                }
            }
        }
    }
});

document.addEventListener("keyup", (event) => {
    if(self && self.posmodel ){
        self.posmodel.keysPressed = {};
        delete self.posmodel.keysPressed[event.key];
    }
});


    }
})