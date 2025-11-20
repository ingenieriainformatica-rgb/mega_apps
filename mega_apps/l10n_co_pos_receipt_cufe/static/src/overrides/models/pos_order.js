import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { qrCodeSrc } from "@point_of_sale/utils";

patch(PosOrder.prototype, {
    /**
     * Verifica si la orden es de Colombia
     */
    is_colombian_country() {
        return this.company.country_id?.code === "CO";
    },

    /**
     * Extiende export_for_printing para agregar información del CUFE
     */
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);

        // Solo para órdenes colombianas
        if (this.is_colombian_country()) {
            // Agregar nombre de orden (compatibilidad con l10n_co_pos)
            result.l10n_co_dian = this.name;

            // Agregar CUFE si la orden tiene factura asociada
            const hasCufe = this.account_move?.l10n_co_edi_cufe_cude_ref;
            const showCufe = this.config.l10n_co_show_cufe_receipt;
            const isDianAccepted = this.account_move?.l10n_co_dian_state === 'invoice_accepted';

            if (hasCufe && showCufe && isDianAccepted) {
                result.l10n_co_cufe = this.account_move.l10n_co_edi_cufe_cude_ref;
                result.l10n_co_cufe_qr = qrCodeSrc(result.l10n_co_cufe, { size: 180 });
                result.l10n_co_show_cufe = true;
            } else {
                result.l10n_co_cufe = false;
                result.l10n_co_cufe_qr = false;
                result.l10n_co_show_cufe = false;
            }
        }

        return result;
    },

    /**
     * Determina si debe esperar a que se procese la orden
     * (útil si queremos facturar automáticamente)
     */
    wait_for_push_order() {
        let result = super.wait_for_push_order(...arguments);
        // Esperar si está configurado para facturación automática en Colombia
        if (this.config.l10n_co_auto_invoice_pos && this.is_colombian_country()) {
            result = true;
        }
        return result;
    },
});
