/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { _t } from "@web/core/l10n/translation";

patch(PosOrder.prototype, {
    add_paymentline(payment_method) {
        // Validar que no se use "Crédito de cliente" con el cliente "Consumidor Final" (id=91158)
        const currentPartner = this.get_partner();
        
        // Verificar si el método de pago es "Crédito de cliente" (Customer Account)
        // El tipo 'pay_later' corresponde a "Customer Account" / "Crédito de cliente"
        if (payment_method && payment_method.type === 'pay_later') {
            // Si no hay cliente seleccionado o es el consumidor final (id=91158)
            if (!currentPartner || currentPartner.id === 91158) {
                // Lanzar error que será capturado por el componente
                throw new Error(
                    _t("No se puede usar el método de pago 'Crédito de cliente' con el cliente 'Consumidor Final'. Por favor, seleccione otro cliente o método de pago.")
                );
            }
        }
        
        // Si la validación pasa, ejecutar el método original
        return super.add_paymentline(...arguments);
    },
});
