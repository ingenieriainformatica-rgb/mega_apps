/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";


export class ZReportOptionPopup extends Component {
    static template = "sh_pos_all_in_one_retail.ZReportOptionPopup";
    static components = {  Dialog };

    setup(){
        super.setup()
        this.pos = usePos();
        this.report = useService("report");
        this.state = useState({
            selected_type : "pdf",
        });
    }
    close() {
        this.props.close();
    }
    async print() {
        var self = this;
        console.log("selected_type ->", this.state.selected_type);
        
        var statementPrintValue = this.state.selected_type;

        if (statementPrintValue) {
            if (statementPrintValue == "pdf") {
                this.report.doAction("sh_pos_all_in_one_retail.pos_z_report_detail", [
                    this.pos.session.id,
                ]);
            } else if (statementPrintValue == "receipt" && self.pos.session && self.pos.session.id) {
                const session_detail = await self.pos.data.call("pos.session", "get_session_detail", [self.pos.session.id]);
                if(session_detail){
                    self.pos.is_z_report_receipt = true
                    self.pos.session_data = session_detail
                    self.pos.showScreen("ReceiptScreen");
                }
            }
        }     
        this.close()       
    }
}
