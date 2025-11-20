/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { ProductQtyPopup } from "@sh_pos_all_in_one_retail/static/sh_pos_wh_stock/app/popups/product_stock_popup/product_stock_popup";
import { ProductStockRestrict } from "@sh_pos_all_in_one_retail/static/sh_pos_wh_stock/app/popups/restrict_sale_popup/restrict_sale_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";


patch(PosStore.prototype, {
    async showStock(id) {
        event.stopPropagation()
        const stocks = this.models["stock.quant"].getAll().filter((quant) => {
            if (quant.product_id && quant.product_id.id == id && quant.location_id && quant.location_id.usage == 'internal') { return true } else { return false }
        })
        
        const warehouseStock = stocks.reduce((acc, { warehouse_id, item, quantity }) => (acc[warehouse_id.display_name] = acc[warehouse_id.display_name] || {}, acc[warehouse_id.display_name][warehouse_id.display_name] = (acc[warehouse_id.display_name][warehouse_id.display_name] || 0) + quantity, acc.total = (acc.total || 0) + quantity, acc),{});
        if (stocks && stocks.length) {
            if (this.config.sh_display_by == "warehouse") {
                this.dialog.add(ProductQtyPopup, {
                    title: _t("Product Stock"),
                    'product_stock': warehouseStock
                });
            } else {
                this.dialog.add(ProductQtyPopup, {
                    title: _t("Product Stock"),
                    'product_stock': stocks,
                });
            }
        } else {
            await this.dialog.add(AlertDialog, {
                title: _t("Stock Warning"),
                body: _t("Product has no stock !"),
            });
        }
    },
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {        
        if (this.config.sh_show_qty_location && this.config.sh_display_stock) {
            var order = this.get_order()
            let  stock_qty = 0
            let sh_min_qty = this.config.sh_min_qty
            const stocks = this.models["stock.quant"].getAll().filter((quant) => {
                if (quant.product_id && quant.product_id.id == vals.product_id.id && quant.location_id && quant.location_id.usage == 'internal'  && quant.location_id.id == this.config.sh_pos_location.id) { return true } else { return false }
            })
            if(stocks && stocks.length){
                 stock_qty = stocks.reduce((sum, stock) => sum + (stock.quantity - stock.sh_qty), 0);
            }
            
            var lines = order.get_orderlines().filter((x) => x.product_id.id == vals.product_id.id)
            if (lines && lines.length) {
                let restrict_popup = false
                let qty = 0.00
                for (let line of lines) {
                    qty += line.qty
                    if (line && line.product_id.id == vals.product_id.id && (stock_qty - qty) <= sh_min_qty) {
                        restrict_popup = true
                    }
                }
                if (restrict_popup) {
                    const confirmed = await new Promise((resolve) => {
                        this.dialog.add(ProductStockRestrict, {
                            title: _t(vals.product_id.display_name),
                            body: _t('Minimum availabe quantity is ' + sh_min_qty),
                            'product': vals.product_id,
                            confirm: resolve.bind(null, true),
                        });
                    })
                    if (confirmed) {
                       return await super.addLineToCurrentOrder(...arguments)
                    }
                } else {
                   return await super.addLineToCurrentOrder(...arguments)
                }
            } else {
                if ((stock_qty - 1) < sh_min_qty) {
                    const confirmed = await new Promise((resolve) => {
                        this.dialog.add(ProductStockRestrict, {
                            title: _t(vals.product_id.display_name),
                            body: _t('Minimum availabe quantity is ' + sh_min_qty),
                            'product': vals.product_id,
                            confirm: resolve.bind(null, true),
                        });
                    })
                    if (confirmed) {
                       return await super.addLineToCurrentOrder(...arguments)
                    }
                } else {
                   return await super.addLineToCurrentOrder(...arguments)
                }
            }
        } else {
           return await super.addLineToCurrentOrder(...arguments)
        }

    }
})
