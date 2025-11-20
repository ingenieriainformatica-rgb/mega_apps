/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { PosZReceipt } from "@sh_pos_all_in_one_retail/static/sh_pos_reports/sh_pos_z_report/overrides/components/receipt_screen/PosZReceipt"


patch(PosStore.prototype, {
    async printReceipt({ basic = false, order = this.get_order() } = {}) {
        if(this.is_z_report_receipt){
            await this.printer.print(
                PosZReceipt,
                {
                    data: this.orderExportForPrinting(order),
                    formatCurrency: this.env.utils.formatCurrency,
                    basic_receipt: basic,
                },
                { webPrintFallback: true }
            );
            return true;
        }else{
            super.printReceipt(...arguments)
        }
    }
});
