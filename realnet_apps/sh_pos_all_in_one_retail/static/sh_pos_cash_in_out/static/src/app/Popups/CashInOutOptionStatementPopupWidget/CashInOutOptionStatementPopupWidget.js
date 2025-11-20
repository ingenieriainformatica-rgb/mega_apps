/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Component, useState, reactive } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";


export class CashInOutOptionStatementPopupWidget extends Component {
    static template = "sh_pos_all_in_one_retail.CashInOutOptionStatementPopupWidget";
    static components = { Dialog };
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.pos = usePos();
        this.report = useService("report");
        this.showStatementDate = useState({
            changeStatementOption: 'current_session',
            statementValue: "receipt",
            start_date: "",
            end_date: "",
        })
    }
    cancel() {
        this.props.close();
    }
    async print() {
        var self = this;
        var statementValue = this.showStatementDate.changeStatementOption
        var statementPrintValue = this.showStatementDate.statementValue
        if (statementValue) {
            let all_cash_in_out_statement = this.props.all_cash_in_out;
            if (statementValue == "current_session" && statementPrintValue == "pdf") {
                if (all_cash_in_out_statement.length) {
                    self.report.doAction("sh_pos_all_in_one_retail.sh_pos_cash_in_out_report", [all_cash_in_out_statement.map(x => x.id)]);
                } else {
                    alert("No Any Cash In / Cash Out Statement for this Session.");
                };
            } else if (statementValue == "current_session" && statementPrintValue == "receipt") {
                if (all_cash_in_out_statement && all_cash_in_out_statement.length) {
                    self.pos.showScreen("CashInOutStatementReceipt", {
                        'all_cash_in_out_statement': all_cash_in_out_statement
                    });
                } else {
                    alert("No Any Cash In / Cash Out Statement avilable.");
                }
            } else if (statementValue == "date_wise" && statementPrintValue == "pdf") {
                if (this.showStatementDate.start_date && this.showStatementDate.end_date) {
                    var start_date = this.showStatementDate.start_date
                    var end_date = this.showStatementDate.end_date
                    let all_cash_in_out_statement =  await this.orm.call("sh.cash.in.out", "search_read", [
                        [['sh_date', '>=', start_date], ["sh_date", "<=", end_date], ["company_id", "=", company_id]]
                    ])
                    if (all_cash_in_out_statement) {
                        if (all_cash_in_out_statement && all_cash_in_out_statement.length > 0) {
                            self.report.doAction("sh_pos_all_in_one_retail.sh_pos_cash_in_out_date_wise_report", [all_cash_in_out_statement.map(x => x.id)]);
                        } else {
                            alert("No Cash In / Out Statement Between Given Date.");
                        }
                    };
                } else {
                    alert("Enter Start Date or End Date.");
                }
            } else if (statementValue == "date_wise" && statementPrintValue == "receipt") {
                if (this.showStatementDate.start_date && this.showStatementDate.end_date) {
                    var start_date = this.showStatementDate.start_date
                    var end_date = this.showStatementDate.end_date
                    let company_id = this.pos.company.id
                    let all_cash_in_out_statement =  await this.orm.call("sh.cash.in.out", "search_read", [
                        [['sh_date', '>=', start_date], ["sh_date", "<=", end_date], ["company_id", "=", company_id]]
                    ])
                    if (all_cash_in_out_statement && all_cash_in_out_statement.length > 0) {
                        if (all_cash_in_out_statement.length > 0) {
                            self.pos.showScreen("CashInOutStatementReceipt", {
                                'all_cash_in_out_statement': all_cash_in_out_statement
                            });
                        } else {
                            alert("No Cash In / Out Statement Between Given Date.");
                        }
                    } else {
                        alert("No Any Cash In / Cash Out Statement avilable.");
                    }
                } else {
                    alert("Enter Start Date or End Date.");
                }
            }
        }
        this.cancel()
    }
}
