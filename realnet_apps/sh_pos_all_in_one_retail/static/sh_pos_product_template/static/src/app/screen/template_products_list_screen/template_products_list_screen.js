/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component } from "@odoo/owl";
import { TemplateProductsLine } from "@sh_pos_all_in_one_retail/static/sh_pos_product_template/app/screen/template_products_line/template_products_line";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export class TemplateProductsListScreenWidget extends Component {
    static template = "sh_pos_all_in_one_retail.TemplateProductsListScreenWidget";
    static components = { TemplateProductsLine };

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.state = {
            query: null,
            selectedTemplate: this.pos.models['pos.product.template'].getAll(),
        };

        this.updateTemplateList = useDebounced(this.updateTemplateList, 70);
    }
    get_all_product_templates() {
        return this.pos.models['pos.product.template'].getAll();
    }
    updateTemplateList(event) {
        this.state.query = event.target.value;
        const templatelistcontents = this.templatelistcontents;
        if (event.code === "Enter" && templatelistcontents.length === 1) {
            this.state.selectedTemplate = templatelistcontents[0];
        } else {
            this.render();
        }
    }
    get_template_by_name(name) {
        var templates = this.get_all_product_templates();
        return templates.filter((template) => {
            if (template["name"]) {
                if (template["name"].indexOf(name) > -1) {
                    return true;
                } else {
                    return false;
                }
            }
        });
    }

    get templatelistcontents() {
        if (this.state.query && this.state.query.trim() !== "") {
            var templates = this.get_template_by_name(this.state.query.trim());
            return templates;
        } else {
            var templates = this.get_all_product_templates();
            return templates;
        }
    }
    back() {
        if (this.state.detailIsShown && !force) {
            this.state.detailIsShown = false;
        } else {
            this.pos.showScreen('ProductScreen')
        }
    }
    get currentOrder() {
        return this.pos.get_order();
    }

    async LoadTemplate(event) {
        var self = this;

        if (this.state.selectedTemplate) {
            var template_lines = this.state.selectedTemplate.pos_product_template_ids
            if (template_lines.length) {
                for (let line of template_lines) {
                    var product_id = line.name ? line.name : false;
                    
                    if (product_id) {
                        if (product_id) {
                            self.pos.addLineToCurrentOrder({
                                product_id: product_id,
                                qty: line.ordered_qty,
                                price_unit: line.unit_price,
                                is_template_product: true,
                            },{});
                            if (line.discount){
                                this.currentOrder.get_selected_orderline().set_discount(line.discount)
                            }
                        }
                    }
                }
            }
            this.pos.showScreen("ProductScreen");
        } else {
            this.dialog.add(AlertDialog, {
                title: _t("Tempate!"),
                body: _t("Please Select Template",),
            });
        }
    }
    clickLine(temp) {
        let template = temp
        if (this.state.selectedTemplate === template) {
            this.state.selectedTemplate = null;
        } else {
            this.state.selectedTemplate = template;
        }
        this.render();
    }

}
registry.category("pos_screens").add("TemplateProductsListScreenWidget", TemplateProductsListScreenWidget);