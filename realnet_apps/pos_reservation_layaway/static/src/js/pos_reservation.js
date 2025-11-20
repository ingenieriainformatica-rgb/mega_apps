/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { ReservationReceipt } from "@pos_reservation_layaway/js/reservation_receipt";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { LayawayPaymentPopup } from "@pos_reservation_layaway/js/layaway_payment_popup";

// Extend the PaymentScreen with layaway actions
patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.orm = useService("orm");
        this.report = useService("report");
        this.printer = useService("printer");
    },

    async _collectInitialPaymentData() {
        const paymentlines = this.paymentLines || this.currentOrder.payment_ids || [];
        let amount = 0.0;
        for (const pl of paymentlines) {
            amount += (typeof pl.get_amount === "function") ? pl.get_amount() : (pl.amount || 0);
        }
        const ref = this.currentOrder.pos_reference || this.currentOrder.name;
        return { amount, journal_id: null, ref };
    },

    async actionLayawayReservation() {
        const order = this.currentOrder;
        const partner = order.get_partner();
        if (!partner) {
            this.dialog.add(AlertDialog, { title: _t("Cliente requerido"), body: _t("Seleccione un cliente para apartar.") });
            return;
        }
        // Validar que no sea Consumidor Final (id=91158)
        if (partner.id === 91158) {
            this.dialog.add(AlertDialog, { 
                title: _t("Cliente no válido"), 
                body: _t("No se puede crear un apartado para el cliente 'Consumidor Final'. Por favor, seleccione otro cliente.") 
            });
            return;
        }
        const linesPayload = order.get_orderlines().map((l) => ({
            product_id: l.get_product().id,
            qty: l.get_quantity(),
            price_unit: l.get_unit_price(),
            discount: l.get_discount(),
            name: l.get_full_product_name(),
        }));
        if (!linesPayload.length) {
            this.dialog.add(AlertDialog, { title: _t("Sin productos"), body: _t("Agregue productos al carrito.") });
            return;
        }
        const initial = await this._collectInitialPaymentData();

        const payload = {
            partner_id: partner.id,
            pricelist_id: (this.currentOrder.pricelist_id && this.currentOrder.pricelist_id.id) || null,
            pos_config_id: this.pos.config.id,
            pos_session_id: this.pos.session && this.pos.session.id,
            user_id: this.pos.user && this.pos.user.id,
            lines: linesPayload,
            initial_payment: initial,
            note: order.general_note || "",
        };

        try {
            const result = await this.orm.call("pos.reservation", "create_from_pos", [payload]);
            const headerData = this.pos.getReceiptHeaderData(this.currentOrder);
            const receiptData = {
                headerData,
                type: "reservation",
                name: result.name,
                partner: partner.name,
                date: (new Date()).toLocaleString(),
                expiration_date: result.expiration_date,
                lines: linesPayload.map((l) => ({
                    name: l.name,
                    qty: l.qty,
                    subtotal: (l.qty || 0) * (l.price_unit || 0) * (1 - (l.discount || 0) / 100),
                })),
                amount_total: result.amount_total,
                amount_paid: result.amount_paid,
                amount_due: result.amount_due,
            };
            await this.printer.print(ReservationReceipt, { data: receiptData, formatCurrency: this.env.utils.formatCurrency }, { webPrintFallback: true });
            this.pos.removeOrder(order);
            this.pos.add_new_order();
            this.pos.showScreen("ProductScreen");
            this.dialog.add(AlertDialog, {
                title: _t("Apartado creado"),
                body: _t("Código: ") + `${result.name}  |  ` + _t("Vence: ") + `${result.expiration_date}`,
            });
        } catch (error) {
            this.dialog.add(AlertDialog, { title: _t("Error"), body: (error && error.message) || _t("No se pudo crear el apartado.") });
            throw error;
        }
    },

    async actionLayawayAddPayment() {
        this.dialog.add(LayawayPaymentPopup, {});
    },
});

// Add entry point from ProductScreen actions
patch(ControlButtons.prototype, {
    async actionLayawayAddPaymentFromProductScreen() {
        this.dialog.add(LayawayPaymentPopup, {});
    },
});

