/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    async addNewPaymentLine(paymentMethod) {
        try {
            // Intentar agregar la línea de pago
            return await super.addNewPaymentLine(paymentMethod);
        } catch (error) {
            // Si hay un error (como el de validación de consumidor final), mostrarlo
            this.dialog.add(AlertDialog, {
                title: _t("Error de Validación"),
                body: error.message || _t("No se puede procesar el pago con este método."),
            });
            return false;
        }
    },
});
