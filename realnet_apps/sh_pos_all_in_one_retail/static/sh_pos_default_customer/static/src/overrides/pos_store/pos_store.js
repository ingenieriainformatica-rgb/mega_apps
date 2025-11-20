
/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

// Patch PosStore para asignar cliente por defecto automáticamente
patch(PosStore.prototype, {
    
    createNewOrder(data = {}) {

        const order = super.createNewOrder(data);
        
        if (this._shouldAssignDefaultPartner(data, order)) {
            const defaultPartner = this.getDefaultPartner();
            if (defaultPartner) {
                order.set_partner(defaultPartner);
                // console.log("Cliente por defecto asignado:", defaultPartner.name);
            }
        }
                
        return order;
    },

    _shouldAssignDefaultPartner(data, order) {

        // Verificar que el POS esté completamente inicializado
        if (!this.models || !this.models["res.partner"]) {
            return false;
        }

        // Detectar contexto de devolución
        if (this._isRefundContext()) {
            console.log("Contexto de devolución detectado - no asignar cliente por defecto");
            return false;
        }

        // No asignar si ya se especificó un partner en los datos
        if (data.partner_id || (order && order.get_partner())) {
            return false;
        }

        // No asignar durante procesos de reembolso o cuando hay órdenes de referencia
        if (data.refund_order_id || data.is_refund || data.refunded_orderline_id) {
            return false;
        }

        // Verificar que los partners estén cargados
        try {
            const partners = this.models["res.partner"].getAll();
            return partners && partners.length > 0;
        } catch (error) {
            console.warn("Error al verificar partners disponibles:", error);
            return false;
        }
    },

    _isRefundContext() {
        try {
            // Método 1: Verificar si estamos en TicketScreen
            if (this.mainScreen && this.mainScreen.name === 'TicketScreen') {
                // Si estamos en TicketScreen, es muy probable que sea contexto de devolución
                return true;
            }

            // Método 2: Verificar si hay una orden seleccionada en TicketScreen
            // Esto funciona porque las devoluciones se inician desde TicketScreen
            if (this.get_order() && this.get_order().uiState && this.get_order().uiState.screen_data) {
                const screenData = this.get_order().uiState.screen_data;
                if (screenData.name === 'TicketScreen') {
                    return true;
                }
            }

            // Método 3: Verificar si hay órdenes con líneas de reembolso siendo procesadas
            const currentOrders = this.models["pos.order"].filter(order => !order.finalized);
            for (const order of currentOrders) {
                if (order.lines && order.lines.some(line => line.refunded_orderline_id)) {
                    // Si hay líneas con refunded_orderline_id, estamos en contexto de devolución
                    return true;
                }
            }

            // Método 4: Verificar call stack (método más robusto)
            const error = new Error();
            const stack = error.stack || '';
            if (stack.includes('onDoRefund') || 
                stack.includes('_getEmptyOrder') || 
                stack.includes('setPartnerToRefundOrder') ||
                stack.includes('TicketScreen')) {
                return true;
            }

            return false;
        } catch (error) {
            console.warn("Error al detectar contexto de devolución:", error);
            // En caso de error, asumir que NO es contexto de devolución
            // para mantener funcionalidad normal
            return false;
        }
    },

    getDefaultPartner() {
        try {
            // Verificar que los modelos estén disponibles
            if (!this.models || !this.models["res.partner"]) {
                return null;
            }

            if (this.config.sh_enable_default_customer && this.config.sh_default_customer_id) {
                return this.config.sh_default_customer_id;
            }

            // Fallback: Buscar cliente "Consumidor final aranzazu" como antes
            const partners = this.models["res.partner"].getAll();
            if (!partners || partners.length === 0) {
                return null;
            }

            const fallbackPartner = partners.find(partner =>
                partner.id === 86941
            );

            return fallbackPartner;
        } catch (error) {
            console.warn("Error al buscar cliente por defecto:", error);
            return null;
        }
    }

});
