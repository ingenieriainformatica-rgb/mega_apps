/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { reactive } from "@odoo/owl";
import { ProductConfiguratorPopup } from "@point_of_sale/app/store/product_configurator_popup/product_configurator_popup"
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { ProductInfoPopup } from "@point_of_sale/app/screens/product_screen/product_info_popup/product_info_popup";

ProductConfiguratorPopup.components["ProductCard"] = ProductCard
patch(ProductConfiguratorPopup.prototype, { 
    get getAlternativeProduct(){        
        return this.props.product?.sh_alternative_products || []
    },
    get getVarientProduct() {
        if (!this.props.product || !this.env.services.pos) {
            return [];
        }
        const pos = this.env.services.pos;
        const allProducts = pos.models["product.product"].getAll().filter(product =>
            product && product.sh_product_tmpl_id === this.props.product.sh_product_tmpl_id
        );    
        return allProducts.filter(product => {
            // Validar que el producto tenga todas las propiedades necesarias
            if (!product || !product.attribute_line_ids || !Array.isArray(product.attribute_line_ids)) {
                return false;
            }
            
            // Asegurar que product_template_variant_value_ids esté inicializado
            if (!product.product_template_variant_value_ids || !Array.isArray(product.product_template_variant_value_ids)) {
                product.product_template_variant_value_ids = [];
            }
            
            return product.attribute_line_ids.every(attributeLine => 
                attributeLine && 
                attributeLine.attribute_id && 
                attributeLine.attribute_id.display_type === 'radio'
            );
        });
    },   
    async onProductInfoClick(product) {
        if (!product || !this.env.services.pos) {
            return;
        }
        
        // Asegurar que product_template_variant_value_ids esté inicializado
        if (!product.product_template_variant_value_ids || !Array.isArray(product.product_template_variant_value_ids)) {
            product.product_template_variant_value_ids = [];
        }
        
        const pos = this.env.services.pos;
        const info = await reactive(pos).getProductInfo(product, 1);
        this.env.services.dialog.add(ProductInfoPopup, { info: info, product: product });
    },
    async addProductToOrder(product) {
        if (!product) {
            return;
        }
        
        // Validar que el producto tenga las propiedades mínimas necesarias
        if (!product.id || !product.display_name) {
            console.error('Product missing required properties:', product);
            return;
        }
        
        // Asegurar que las propiedades de array existan y sean arrays válidos
        if (!product.attribute_line_ids || !Array.isArray(product.attribute_line_ids)) {
            product.attribute_line_ids = [];
        }
        
        // CRÍTICO: Inicializar product_template_variant_value_ids para evitar el error "Cannot read properties of undefined (reading 'includes')"
        if (!product.product_template_variant_value_ids || !Array.isArray(product.product_template_variant_value_ids)) {
            product.product_template_variant_value_ids = [];
        }
        
        // Inicializar propiedades de arrays que son secundarias pero críticas
        product.attribute_line_ids.forEach(attributeLine => {
            if (!attributeLine.product_template_value_ids || !Array.isArray(attributeLine.product_template_value_ids)) {
                attributeLine.product_template_value_ids = [];
            }
        });
        
        if (!product.pos_categ_ids || !Array.isArray(product.pos_categ_ids)) {
            product.pos_categ_ids = [];
        }
        if (!product.tax_ids || !Array.isArray(product.tax_ids)) {
            product.tax_ids = [];
        }
        if (!product.taxes_id || !Array.isArray(product.taxes_id)) {
            product.taxes_id = [];
        }
        if (!product.pack_lot_ids || !Array.isArray(product.pack_lot_ids)) {
            product.pack_lot_ids = [];
        }
        if (!product.sh_topping_ids || !Array.isArray(product.sh_topping_ids)) {
            product.sh_topping_ids = [];
        }
        if (!product.sh_alternative_products || !Array.isArray(product.sh_alternative_products)) {
            product.sh_alternative_products = [];
        }
        
        // Para productos variantes específicos, no necesitamos pasar por el sistema de configuración
        // de atributos. Simplemente agregamos el producto específico directamente al carrito
        try {
            const pos = this.env.services.pos;
            await pos.addLineToCurrentOrder({
                product_id: product,
                qty: 1,
                merge: false
            }, {}, false); // configure=false para evitar abrir otro configurador
            
            this.props.close();
        } catch (error) {
            console.error('Error adding product to order:', error);
            // Si hay error, intentemos con el método original del popup
            this.props.getPayload({
                attribute_value_ids: [],
                attribute_custom_values: {},
                price_extra: 0,
                qty: 1
            });
            this.props.close();
        }
    }
})
