/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { ZReportOptionPopup } from "@sh_pos_all_in_one_retail/static/sh_pos_reports/sh_pos_z_report/app/Popups/ZReportOptionPopup/ZReportOptionPopup";
import { ZReportPostedSessionOptionPopup } from "@sh_pos_all_in_one_retail/static/sh_pos_reports/sh_pos_z_report/app/Popups/ZReportPostedSessionOptionPopup/ZReportPostedSessionOptionPopup";

patch(ControlButtons.prototype, {
    setup() {
        super.setup()
        this.report = useService("report");
    },
    async printPostedSessionReport(){
        var self = this;
        let posted_session_list = self.pos.session._posted_session
        console.log("posted_session_list", posted_session_list);
        if(posted_session_list){
            await this.dialog.add(ZReportPostedSessionOptionPopup);
        }else{
            alert("No Any Posted Session Found.")
        }
    },
    async onClickZreport(){
        var self = this;
        if(self && self.pos && self.pos.config && self.pos.config.sh_allow_z_report_type && self.pos.config.sh_allow_z_report_type == 'pdf'){
            this.report.doAction("sh_pos_all_in_one_retail.pos_z_report_detail", [this.pos.session.id,]);
        }else if(self && self.pos && self.pos.config && self.pos.config.sh_allow_z_report_type && self.pos.config.sh_allow_z_report_type == 'receipt' && self.pos.session && self.pos.session.id){
            const session_detail = await self.pos.data.call("pos.session", "get_session_detail", [self.pos.session.id]);
            if(session_detail){
                self.pos.is_z_report_receipt = true
                self.pos.session_data = session_detail
                self.pos.showScreen("ReceiptScreen");
            }
        }else if(self && self.pos && self.pos.config && self.pos.config.sh_allow_z_report_type && self.pos.config.sh_allow_z_report_type == 'both' && self.pos.session && self.pos.session.id){
            await this.dialog.add(ZReportOptionPopup);
        }
    }
});
