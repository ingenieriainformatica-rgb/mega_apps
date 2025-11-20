/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

/**
 * Componente para el recibo de factura electrónica de apartado
 * Integra con sh_pos_all_in_one_retail y l10n_co_dian para mostrar CUFE y QR
 */
export class LayawayInvoiceReceipt extends Component {
    static template = "pos_reservation_layaway.LayawayInvoiceReceipt";

    setup() {
        this.pos = usePos();
    }

    /**
     * Getter para acceder a los datos desde el template
     */
    get data() {
        return this.props.data || {};
    }

    /**
     * Formatea un valor monetario usando la función pasada por props o fallback
     */
    formatCurrency(amount, showSymbol = true) {
        // Usar la función pasada por props si está disponible
        if (this.props.formatCurrency && typeof this.props.formatCurrency === 'function') {
            return this.props.formatCurrency(amount, showSymbol);
        }
        
        // Fallback usando el POS
        if (this.pos && this.pos.env && this.pos.env.utils && this.pos.env.utils.formatCurrency) {
            return this.pos.env.utils.formatCurrency(amount, showSymbol);
        }
        
        // Fallback manual
        const formatted = parseFloat(amount || 0).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        return showSymbol ? `$ ${formatted}` : formatted;
    }
}

LayawayInvoiceReceipt.props = {
    data: { type: Object, optional: false },
    formatCurrency: { type: Function, optional: true },
};
