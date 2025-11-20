/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ReturnOrderPopup } from "@sh_pos_all_in_one_retail/static/sh_pos_order_return_exchange/apps/popups/return_order_popup/return_order_popup";


patch(ReturnOrderPopup.prototype,{
  setup(){
    super.setup();
   
  },
  onClickRadio(ev){
    console.log(ev.target.value);
    console.log(this.props);
    

    var button_value = ev.target.value;

    if (button_value == "Return") {
      this.state.show_exchange_button = false;
      this.state.show_return_buttons = true;
      console.log(this.props);
      
    }else if (button_value == "Exchange") {
      this.state.show_return_buttons = false;
      this.state.show_exchange_button = true;
    }
    
  }
});
