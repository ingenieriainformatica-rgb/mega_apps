/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, useState, reactive } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";


export class ReturnOrderPopup extends Component {
    static template = "sh_pos_return_exchange.ReturnOrderPopup";
    static components = { Dialog };
    setup() {
        super.setup();
        this.pos = usePos()
        this.returnLines = []
        this.order = this.props.order
        this.state = useState({
            return: Object.fromEntries(this.props.lines.map((line) => [line.id, 0])),
            is_exchange_checked: true,
            show_return_buttons : this.props.sh_return_order,
            show_exchange_button : this.props.exchange_order,
        })

    }
    sh_input_qty(line_id, val, max_val) {
        if (!this.pos.config.sh_return_more_qty) {
            if (parseFloat(val) > parseFloat(max_val)) {
                this.state.return[line_id] = 0
            }
        } else {
            if (this.props.exchange_order && parseFloat(val) > parseFloat(max_val)) {
                this.state.return[line_id] = 0
            }
        }
    }

    async sh_exchange(ev) {
        var self = this;
        var order = this.pos.get_order()
        if (this.state.return) {
            [...order.get_orderlines()].map(async (line) => await order.removeOrderline(line))

            if (this.order && this.order.partner_id) {
                order.set_partner(this.order.partner_id)
            }
            for (let return_line of Object.keys(this.state.return)) {
                if (this.state.return[return_line]) {
                    let line_data = self.pos.models['pos.order.line'].get(return_line)
                    await this.pos.addLineToCurrentOrder({
                        product_id: line_data.product_id,
                        qty: -(parseFloat(this.state.return[return_line])),
                        merge: false, 
                        price_unit: line_data.price_unit
                    }, {}, false);

                    if (this.state.is_exchange_checked){
                        await this.pos.addLineToCurrentOrder({
                            product_id: line_data.product_id,
                            qty: parseFloat(this.state.return[return_line]),
                            merge: false, 
                            price_unit: line_data.price_unit
                        }, {}, false);
                    }
                    
                }
            }
            order.is_exchange_order = true
            order.old_pos_reference = this.order.pos_reference
            order.old_pos_order_id = this.order.id

            this.cancel()
            self.pos.showScreen('ProductScreen')
        }
    }

    async sh_total_exchange(ev) {
        var self = this;
        var order = this.pos.get_order();
        if (this.returnLines) {
            [...order.get_orderlines()].map(async (line) => await order.removeOrderline(line))
            if (this.order && this.order.partner_id) {
                var partner = this.pos.db.get_partner_by_id(this.order.partner_id)
                order.set_partner(partner)
            }
            for (let return_line of this.props.lines) {
                if (return_line) {
                    let qty = return_line.qty
                    var exchange_same_product = $('#exchange_checkbox').is(':checked')
                    if ((qty - return_line.sh_return_qty) > 0) {
                        let product = self.pos.db.get_product_by_id(return_line.product_id)
                        if (product && (!product.sh_product_non_exchangeable)) {
                            order.add_product(product, {
                                quantity: -(qty - return_line.sh_return_qty),
                                price: return_line.price_unit,
                                'sh_line_id': return_line.id
                            })
                            if (exchange_same_product) {
                                order.add_product(product, {
                                    quantity: qty - return_line.sh_return_qty,
                                    price: return_line.price_unit,
                                    merge: false,
                                })
                            }
                        }
                    }
                }
            }
            order.is_exchange_order = true
            order.old_pos_reference = this.order.pos_reference
            order.old_pos_order_id = this.order.id

            this.confirm()
            self.pos.showScreen('ProductScreen')
        }
    }
    async sh_total_retun(ev) {
        var self = this;
        [...this.pos.get_order().get_orderlines()].map(async (line) => await this.pos.get_order().removeOrderline(line))
        
        var order = this.pos.get_order()
        if (this.order && this.order.partner_id) {
            order.set_partner(this.order.partner_id)
        }
        for (let return_line of this.props.lines) {
            await this.pos.addLineToCurrentOrder({
                product_id: return_line.product_id,
                qty: -(parseFloat(return_line.qty)),
            }, {}, false);
            
        }
        order.is_return_order = true
        order.old_pos_reference = this.order.pos_reference
        order.old_pos_order_id = this.order.id

        this.cancel()
        this.env.services.pos.showScreen("PaymentScreen", {
            orderUuid: order.uuid,
        });
        
    }
    async sh_retun() {
        var self = this;
        var order = this.pos.get_order()
        if (this.state.return) {
            [...order.get_orderlines()].map(async (line) => await order.removeOrderline(line))

            if (this.order && this.order.partner_id) {
                order.set_partner(this.order.partner_id)
            }
            for (let return_line of Object.keys(this.state.return)) {
                if (this.state.return[return_line]) {
                    let line_data = self.pos.models['pos.order.line'].get(return_line)
                    await this.pos.addLineToCurrentOrder({
                        product_id: line_data.product_id,
                        qty: -(parseFloat(this.state.return[return_line])),
                    }, {}, false);
                }
            }

            order.is_return_order = true
            order.old_pos_reference = this.order.pos_reference || this.order.name
            order.old_pos_order_id = this.order.id || this.order.server_id
            this.cancel()
            this.env.services.pos.showScreen("PaymentScreen", {
                orderUuid: order.uuid,
            });
        }
    }
    getPayload() {
        return ""
    }
    cancel() {
        this.props.close()
    }
}
