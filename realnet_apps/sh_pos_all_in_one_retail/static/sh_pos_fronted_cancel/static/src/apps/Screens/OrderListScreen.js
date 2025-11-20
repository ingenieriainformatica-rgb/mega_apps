/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { OrderListScreen } from "@sh_pos_all_in_one_retail/static/sh_pos_order_list/apps/screen/order_list_screen/order_list_screen";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(OrderListScreen.prototype, {
    setup() {
        this.orm = useService("orm");
        super.setup(...arguments);
    },
  

    click_draft(ev, order) {
        ev.stopPropagation()
         this.orm.call(
            "pos.order",                 
            "sh_fronted_cancel_draft",  
            [[order.id]]                  
        )
        order.state='draft'
        this.render(true)
    },
    
    async click_delete(ev, order) {
        ev.stopPropagation()
        await this.orm.call(
            "pos.order",                 
            "sh_fronted_cancel_delete",  
            [[order.id]]                  
        )
        await this.pos.models['pos.order'].delete(order)
        this.render(true)
    },


       
    async click_cancel(ev, order){   
        ev.stopPropagation()
        await this.orm.call(
            "pos.order",                 
            "sh_fronted_cancel",  
            [[order.id]]                  
        )
        order.state='cancel'
        this.render(true)
    }
})
