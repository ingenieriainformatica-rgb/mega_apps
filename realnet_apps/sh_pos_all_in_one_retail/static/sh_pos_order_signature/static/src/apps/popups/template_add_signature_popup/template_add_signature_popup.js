/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, useState, onWillStart, useRef,useEffect } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { NameAndSignature } from "@web/core/signature/name_and_signature";

export class TemplateAddSignaturePopupWidget extends Component {
    static template = "sh_enable_order_signature.TemplateAddSignaturePopupWidget";
    static components = { Dialog , NameAndSignature };

    setup(){
        super.setup()
        this.pos = usePos();
        this.state = useState({
            sh_date: "",
            sh_name: "",
        });
        let partner_name = this.pos.get_order().get_partner() ? this.pos.get_order().get_partner().name : false
        this.signature = useState({ name: partner_name ? partner_name : " " });
        this.nameAndSignatureProps = {
            signature: this.signature,
        };

        onWillStart(async () => {
            if (this.pos.config.sh_enable_date) {
                var today = new Date();
                var dd = String(today.getDate()).padStart(2, "0");
                var mm = String(today.getMonth() + 1).padStart(2, "0");
                var yyyy = today.getFullYear();
                today = yyyy + "-" + mm + "-" + dd;
                this.state.sh_date = today
            }
        })

        this.signatureRef = useRef("signature");
        
        
    }
    confirm() {
        var self = this;
        if (this.signature.getSignatureImage() && this.signature.getSignatureImage().split(",")[1]) {
            self.pos.get_order().set_signature(this.signature.getSignatureImage().split(",")[1]);
        }
        if (self.pos.config.sh_enable_name) {
            var name = this.state.sh_name;
            if (name) {
                self.pos.get_order().set_signature_name(name);
            }
        }
        if (self.pos.config.sh_enable_date) {
            var date = this.state.sh_date;
            if (date) {
                self.pos.get_order().set_signature_date(date);
            }
        }
        this.props.close();
    }
    cancel() {
        this.props.close();
    }
}
