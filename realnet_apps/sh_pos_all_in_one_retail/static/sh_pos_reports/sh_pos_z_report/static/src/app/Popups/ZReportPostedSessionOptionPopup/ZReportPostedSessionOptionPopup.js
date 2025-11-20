/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class ZReportPostedSessionOptionPopup extends Component {
    static template = "sh_pos_all_in_one_retail.ZReportPostedSessionOptionPopup";
    static components = {  Dialog };

    setup() {
        super.setup();
        this.pos = usePos();
        this.report = useService("report");
        this.state = useState({
            selectedSession : "",
            selectedoption : ""
        });
    }
    get posted_session_list(){
        return  this.pos.session._posted_session
    }
    async print(){
        var self = this;
        var sessionSelection = this.state.selectedSession;
        if(sessionSelection){
            if(self.pos.config.sh_allow_z_report_type == 'both'){
                var statementPrintValue = self.state.selectedoption;
                if(sessionSelection && statementPrintValue){
                    if (statementPrintValue == "pdf") {
                        this.report.doAction("sh_pos_all_in_one_retail.pos_z_report_detail", [
                            sessionSelection,
                        ]);
                    } else if (statementPrintValue == "receipt") {
                        
                        const session_detail = await self.pos.data.call("pos.session", "get_session_detail", [
                            parseInt(sessionSelection)
                        ]);
                        if(session_detail){
                            self.pos.is_z_report_receipt = true
                            self.pos.session_data = session_detail
                            self.pos.showScreen("ReceiptScreen");
                        }
                    }
                }
            }else if(self.pos.config.sh_allow_z_report_type == 'pdf'){
                this.report.doAction("sh_pos_all_in_one_retail.pos_z_report_detail", [
                    parseInt(sessionSelection),
                ]);
            }else if(self.pos.config.sh_allow_z_report_type == 'receipt'){
                const session_detail = await self.pos.data.call("pos.session", "get_session_detail", [
                    parseInt(sessionSelection)
                ]);
                if(session_detail){
                    self.pos.is_z_report_receipt = true
                    self.pos.session_data = session_detail
                    self.pos.showScreen("ReceiptScreen");
                }
            }

        }else{
            alert("No Any Posted Session Selected.")
        }
        
        this.close()
    }
    close() {
        this.props.close();
    }
}
