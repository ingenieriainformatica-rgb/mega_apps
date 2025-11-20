/** @odoo-module */

import { Chrome } from "@point_of_sale/app/pos_app";
import { patch } from "@web/core/utils/patch";
import { Component, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { _t } from "@web/core/l10n/translation";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { makeAwaitable, ask } from "@point_of_sale/app/store/make_awaitable_dialog";


patch(Chrome.prototype, {
    setup(){
        super.setup(...arguments)
        this.dialog = useService("dialog");

       this.sh_start()
    },
    async checkPin(employee, pin = false) {
        let inputPin = pin;
        if (!pin) {
            inputPin = await makeAwaitable(this.dialog, NumberPopup, {
                formatDisplayedValue: (x) => x.replace(/./g, "•"),
                title: _t("Password?"),
            });
        } else {
            if (employee._pin !== Sha1.hash(inputPin)) {
                inputPin = await makeAwaitable(this.dialog, NumberPopup, {
                    formatDisplayedValue: (x) => x.replace(/./g, "•"),
                    title: _t("Password?"),
                });
            this.pos.is_timer_screen = false;

            }
        }
        if (!inputPin || employee._pin !== Sha1.hash(inputPin)) {
            alert("Incorrect Password")
            if(this.pos.is_timer_screen){
                $(".pos").before('<div class="blur_screen"><h3>Tap to unlock...</h3></div>');
            }
            return false;
        }
        return true;
    },
    sh_start() {
        var self = this;
        let pin = false;
        if (this.pos.config.sh_enable_auto_lock) {
            var set_logout_interval = function (time) {
                time = time || self.pos.config.sh_lock_timer * 1000;
                if (time) {
                    self.pos.logout_timer = setTimeout(function () {
                        self.pos.is_timer_screen = true
                        $(".pos").before('<div class="blur_screen"><h3>Tap to unlock...</h3></div>');
                    }, time);
                }
            };
        }
        if (this.pos.config.sh_enable_auto_lock && this.pos.config.sh_lock_timer) {
            $(document).on("click", async function (event) {
                if (self.pos.config.sh_enable_auto_lock && self.pos.config.sh_lock_timer) {
                    clearTimeout(self.pos.logout_timer);
                    set_logout_interval();
                    if ($(".blur_screen").length > 0) {
                        if(!self.pos.is_not_remove_screen){
                            $(".blur_screen").remove();
                        }else{
                            self.pos.is_not_remove_screen = false
                        }
                        const current = Component.current;
                        if (self.pos.config.module_pos_hr) {

                            const list = self.pos.models["hr.employee"]
                            .filter((employee) => employee.id !== self.pos.get_cashier().id)
                            .map((employee) => {
                                return {
                                    id: employee.id,
                                    item: employee,
                                    label: employee.name,
                                    isSelected: false,
                                };
                            });
                            const employee = await makeAwaitable(self.dialog, SelectionPopup, {
                                title: _t("Change Cashier"),
                                list: list,
                            });
                            if (!employee || (employee._pin && !(await self.checkPin(employee, pin)))) {
                                return;
                            }else{
                                self.pos.set_cashier(employee);
                                self.pos.is_timer_screen = false;
                            }
                           
                        }else{
                            self.pos.is_timer_screen = false;
                        }
                    }
                }
            });
            set_logout_interval();
        }

    }
});
