/** @odoo-module */

// import { PartnerListScreen } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";
import {PartnerList} from "@point_of_sale/app/screens/partner_list/partner_list";
import { usePos } from "@point_of_sale/app/store/pos_hook";


patch(PartnerList.prototype, {
    setup() {
        super.setup();
        this.customer_list = [];
        this.pos = usePos();
    },
    getPartners() {
        const result = super.getPartners();
        if (this.pos.config.sh_enable_own_customer) {
            if (this.pos.user._role != 'manager'){
                console.log(this.pos.user._role);
                let own_record = []
                for (let index = 0; index < result.length; index++) {
                    const partner = result[index];
                    const record= partner.sh_own_customer                
                    if( record.length > 0 ){
                        own_record.push(partner);
                    }   
                    
                }
                return own_record;
            }
            else {
                return result;
            }
        }else{
            return result;
        }
    }    
});
