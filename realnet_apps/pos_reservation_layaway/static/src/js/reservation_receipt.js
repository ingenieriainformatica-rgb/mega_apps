/** @odoo-module */

import { Component } from "@odoo/owl";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";

export class ReservationReceipt extends Component {
    static template = "pos_reservation_layaway.ReservationReceipt";
    static components = { ReceiptHeader };
    static props = {
        data: Object,
        formatCurrency: Function,
    };
}

