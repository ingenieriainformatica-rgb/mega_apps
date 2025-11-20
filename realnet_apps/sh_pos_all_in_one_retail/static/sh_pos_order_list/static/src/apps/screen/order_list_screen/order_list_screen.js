/** @odoo-module **/

import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { formatDateTime, parseDateTime } from "@web/core/l10n/dates";
import { parseUTCString } from "@point_of_sale/utils";

export class OrderListScreen extends Component {
    static template = "sh_pos_order_list.OrderListScreen";
    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.hardwareProxy = useService("hardware_proxy");
        this.search_filter = false
        this.ordersToShow = this.pos.models['pos.order'].filter((order) => typeof order.id === "number")
        this.currentPage = 1;
        this.limit = 0
        this.totalCount = this.ordersToShow.length;
        this.nPerPage = this.pos.config.sh_how_many_order_per_page;
        this.offset = this.nPerPage + (this.currentPage - 1) * this.nPerPage;
        this.state = useState({
            search_word: ""
        })
    }
    get currentOrder() {
        if (this.pos.get_order()) {
            return this.pos.get_order()
        } else {
            return false
        }
    }
    formate_date_time(date_time){
        return formatDateTime(parseUTCString(date_time))
    }
    async print_pos_order(order) {
        event.stopPropagation()
        if (order) {
            if (this.pos.config.sh_enable_a3_receipt || this.pos.config.sh_enable_a4_receipt || this.pos.config.sh_enable_a5_receipt) {
                if (this.pos.config.sh_default_receipt) {
                    this.hardwareProxy.pos.receipt_type = this.pos.config.sh_default_receipt;
                }
            }else if(!this.pos.config.sh_enable_a3_receipt || !this.pos.config.sh_enable_a4_receipt || !this.pos.config.sh_enable_a5_receipt){
                this.hardwareProxy.pos.receipt_type = false;
            }
            this.pos.printReceipt({ order: order, sh_reprint: true });
        }
    }
    async reorder_pos_order(order) {
        var self = this;
        event.stopPropagation()
        if (order) {
            var order_lines = self.pos.get_order().get_orderlines();
            [...order_lines].map(async (line) => await self.currentOrder.removeOrderline(line));
            if (order.partner_id){
                await self.currentOrder.set_partner(order.partner_id)
            }
            if (order.lines) {
                for (let line of order.lines) {
                    var product = line.product_id
                    if (product) {
                        await this.pos.addLineToCurrentOrder({
                            product_id: product,
                            qty: line.qty,
                            customerNote: line.customer_note || null,
                        }, {}, false);
                        if (line.discount) {
                            self.currentOrder.get_selected_orderline().set_discount(line.discount)
                        }
                    }
                }
                self.back()
            }
        }
    }
    sh_appy_search(search) {
        return this.ordersToShow.filter(function (template) {
            if (template.name.indexOf(search) > -1) {
                return true;
            } else if (template["pos_reference"].indexOf(search) > -1) {
                return true;
            } else if (template.partner_id && (template.partner_id.name.indexOf(search) > -1 || template.partner_id.name.toLowerCase().indexOf(search) > -1)) {
                return true;
            } else if (template["state"] && template["state"].indexOf(search) > -1) {
                return true;
            } else if (template["date_order"] && template["date_order"].indexOf(search) > -1) {
                return true;
            } else {
                return false;
            }
        })
    }
    get get_orders() {
        if (this.search_filter) {
            return this.filteredOrders.slice(this.limit, this.offset);
        } else {
            return this.ordersToShow.slice(this.limit, this.offset);
        }
    }
    async updateOrderList(event) {
        var search = event.target.value;
        if (search) {
            var Orders = await this.sh_appy_search(search)
            this.search_filter = true
            this.filteredOrders = Orders
        } else {
            this.search_filter = false
            this.filteredOrders = []
        }
        this.render(true)
    }
    async change_date(event) {
        let search = event.target.value;
        if (search) {
            var Orders = await this.sh_appy_search(search)
            this.search_filter = true
            this.filteredOrders = Orders
            this.render(true)
        } else {
            this.search_filter = false
            this.filteredOrders = []
        }
    }
    async ShApplyFilter(ev) {
        let search = ev.target.value;
        if (search == "all") {
            this.search_filter = false
            this.filteredOrders = []
        } else {
            this.search_filter = true
            var Orders = await this.sh_appy_search(search)
            this.filteredOrders = Orders
        }
        this.render(true)
    }
    onNextPage() {
        if (this.currentPage <= this.lastPage) {
            this.currentPage += 1;
            this.limit = this.offset;
            this.offset = this.nPerPage + (this.currentPage - 1) * this.nPerPage;
            this.render()
        }
    }
    onPrevPage() {
        if (this.currentPage - 1 > 0) {
            this.currentPage -= 1;
            this.limit = this.nPerPage + (this.currentPage - 1 - 1) * this.nPerPage;
            this.offset = this.limit + this.nPerPage;
            this.render()
        }
    }
    get lastPage() {
        let nItems = 0
        if (this.search_filter) {
            nItems = this.filteredOrders.length;
            return Math.ceil(nItems / (this.nPerPage));
        } else {
            nItems = this.totalCount;
            return Math.ceil(nItems / (this.nPerPage));
        }
    }
    get pageNumber() {
        const currentPage = this.currentPage;
        const lastPage = this.lastPage;        
        return isNaN(lastPage) ? "" : `(${currentPage}/${lastPage})`;
    }
    clear_search() {
        this.state.search_word = ""
        this.search_filter = false
        this.filteredOrders = []
        this.render(true)
    }
    clickLine(orderlist) {
        if(this.show_lines == orderlist.id){
            this.show_lines = 0
        }else{
            this.show_lines = orderlist.id
        }
        this.render(true)
    }
    back() {
        this.pos.showScreen('ProductScreen')
    }
}
registry.category("pos_screens").add("OrderListScreen", OrderListScreen);
