/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async processServerData() {
        await super.processServerData(...arguments);
        this.all_key = [];
        this.all_key_screen = [];
        this.key_screen_by_id = {};
        this.key_by_id = {};
        this.screen_by_key = {};
        this.keysPressed = {};
        this.pressedKeyList = [];
        this.key_screen_by_grp = {};
        this.key_payment_screen_by_grp = {};
        this.temp_key_by_id = {};
        this.keyboard_keys_temp =this.models["sh.keyboard.key.temp"].getAll();
        this.loadKeyboardKeysTemp(this.models["sh.keyboard.key.temp"].getAll());
        this.keyboard_keys = this.models["sh.pos.keyboard.shortcut"].getAll();
        this.loadKeyboardKeys(this.keyboard_keys);
    },
    loadKeyboardKeysTemp(keyboard_keys_temp){
        var self = this
        if(keyboard_keys_temp && keyboard_keys_temp.length > 0){
            self.all_key = keyboard_keys_temp;
            for(let each_key of Object.values(keyboard_keys_temp)){
                if (each_key && each_key.name) {
                    self.temp_key_by_id[each_key.id] = each_key;
                }
            };
        }
    },
    loadKeyboardKeys(keyboard_keys){
        var self = this
        if(keyboard_keys && keyboard_keys.length > 0){
            self.all_key_screen = keyboard_keys;
            for(let each_key_data of keyboard_keys){
                
                var key_combine = "";
                for(let each_key of each_key_data['sh_key_ids']){
                    if (key_combine != "") {
                        key_combine = key_combine + "+" + self.temp_key_by_id[each_key.id]["name"];
                    } else {
                        key_combine = self.temp_key_by_id[each_key.id]["name"];
                    }
                };
                if (each_key_data.payment_method_id ) {
                    self.screen_by_key[key_combine] = each_key_data["payment_method_id"].id;
                    
                    self.key_screen_by_id[each_key_data["payment_method_id"]] = key_combine;
                    if (each_key_data["sh_payment_shortcut_screen_type"]) {
                        if (self.key_payment_screen_by_grp[each_key_data["sh_payment_shortcut_screen_type"]]) {
                            self.key_payment_screen_by_grp[each_key_data["sh_payment_shortcut_screen_type"]].push(each_key_data["payment_method_id"]);
                        } else {
                            self.key_payment_screen_by_grp[each_key_data["sh_payment_shortcut_screen_type"]] = [each_key_data["payment_method_id"]];
                        }
                    }
                } else {
                    self.key_screen_by_id[each_key_data["sh_shortcut_screen"]] = key_combine;
                    if (each_key_data.sh_shortcut_screen_type) {
                        if (self.key_screen_by_grp[each_key_data.sh_shortcut_screen_type]) {
                            self.key_screen_by_grp[each_key_data.sh_shortcut_screen_type].push(each_key_data["sh_shortcut_screen"]);
                        } else {
                            self.key_screen_by_grp[each_key_data.sh_shortcut_screen_type] = [each_key_data["sh_shortcut_screen"]];
                        }
                        
                    }
                }
            };
        }
    }
});

