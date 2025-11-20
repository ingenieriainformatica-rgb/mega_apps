/** @odoo-module **/
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { ProductStockRestrict } from "@sh_pos_all_in_one_retail/static/sh_pos_wh_stock/app/popups/restrict_sale_popup/restrict_sale_popup";
import { _t } from "@web/core/l10n/translation";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";

patch(OrderSummary.prototype, {
    async _setValue(val) {
        var self = this;
        const selectedLine = this.currentOrder.get_selected_orderline();
        if (selectedLine && this.pos.config.sh_display_stock && this.pos.config.sh_show_qty_location) {
            const { numpadMode } = this.pos;
            if (numpadMode === "quantity") {
             const stocks = this.pos.models["stock.quant"].find((quant) => (quant.product_id && quant.product_id.id == selectedLine.product_id.id) && quant.location_id.id == self.pos.config.sh_pos_location.id)
                if (stocks) {
                    var sh_min_qty = this.pos.config.sh_min_qty
                    if (stocks ) {
                        let qty = stocks.quantity - parseFloat(val)
                        if (sh_min_qty > qty) {
                            const confirmed = await new Promise((resolve) => {
                                this.dialog.add(ProductStockRestrict, {
                                    title: _t(selectedLine.product_id.display_name),
                                    body: _t('Minimum availabe quantity is ' + sh_min_qty),
                                    'product': selectedLine.product_id,
                                    confirm: resolve.bind(null, true),
                                    close:  resolve.bind(null, false),
                                });
                            })

                            if (!confirmed) {
                                this.numberBuffer.reset();
                            }
                            else{
                                selectedLine.set_quantity(val);
                            }
                        } else {
                            super._setValue(val);
                        }
                    } else {
                        super._setValue(val);
                    }
                } else {
                    super._setValue(val);
                }
            }
        } else {
            super._setValue(val);
        }
    }
})