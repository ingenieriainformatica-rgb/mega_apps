/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ReservationReceipt } from "@pos_reservation_layaway/js/reservation_receipt";
import { LayawayInvoiceReceipt } from "@pos_reservation_layaway/js/layaway_invoice_receipt";

export class LayawayPaymentPopup extends Component {
    static template = "pos_reservation_layaway.LayawayPaymentPopup";
    static components = { Dialog };

    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.printer = useService("printer");
        this.pos = usePos();
        this.notification = useService("notification");
        this.state = useState({ 
            selectedPartner: null,
            partnerSearch: "",
            partners: [],
            showPartnerList: false,
            reservations: [],
            selectedReservationId: null,
            amount: 0, 
            resv: null, 
            loading: false, 
            error: "",
            paymentMethods: [],
            selectedPaymentMethod: null,
            changeAmount: 0,
            showChange: false
        });
        
        // Cargar métodos de pago disponibles
        this.loadPaymentMethods();
    }

    async loadPaymentMethods() {
        try {
            console.log("=== Cargando métodos de pago ===");
            console.log("POS object:", this.pos);
            console.log("POS config:", this.pos.config);
            
            // Opción 1: Intentar obtener directamente desde this.pos.payment_methods
            if (this.pos.payment_methods && this.pos.payment_methods.length > 0) {
                console.log("Payment methods encontrados en this.pos.payment_methods:", this.pos.payment_methods);
                const journals = [];
                for (const pm of this.pos.payment_methods) {
                    console.log("Payment method:", pm);
                    if (pm.journal_id) {
                        const journalId = Array.isArray(pm.journal_id) ? pm.journal_id[0] : pm.journal_id;
                        journals.push({
                            id: pm.id,  // Usar el ID del payment method como clave única
                            journal_id: journalId,  // El journal_id real para el backend
                            name: pm.name,
                            payment_method_id: pm.id
                        });
                    }
                }
                
                console.log("Journals extraídos:", journals);
                this.state.paymentMethods = journals;
                
                if (journals.length > 0) {
                    this.state.selectedPaymentMethod = journals[0].journal_id;
                    console.log("Método seleccionado por defecto:", journals[0]);
                }
                return;
            }
            
            // Opción 2: Buscar en pos.config.payment_method_ids
            const posConfig = this.pos.config;
            console.log("POS Config payment_method_ids:", posConfig?.payment_method_ids);
            
            if (posConfig && posConfig.payment_method_ids && posConfig.payment_method_ids.length > 0) {
                // Convertir el Proxy/Array a un array simple de IDs
                const paymentMethodIds = Array.from(posConfig.payment_method_ids).map(pm => {
                    return typeof pm === 'object' ? pm.id : pm;
                });
                
                console.log("Payment method IDs extraídos:", paymentMethodIds);
                
                const paymentMethods = await this.orm.searchRead("pos.payment.method", [
                    ["id", "in", paymentMethodIds]
                ], ["id", "name", "journal_id"]);
                
                console.log("Payment methods de searchRead:", paymentMethods);
                
                const journals = [];
                for (const pm of paymentMethods) {
                    if (pm.journal_id && pm.journal_id.length === 2) {
                        journals.push({
                            id: pm.id,  // Usar el ID del payment method como clave única
                            journal_id: pm.journal_id[0],  // El journal_id real para el backend
                            name: pm.name || pm.journal_id[1],
                            payment_method_id: pm.id
                        });
                    }
                }
                
                console.log("Journals extraídos:", journals);
                this.state.paymentMethods = journals;
                
                if (journals.length > 0) {
                    this.state.selectedPaymentMethod = journals[0].journal_id;
                    console.log("Método seleccionado por defecto:", journals[0]);
                }
            } else {
                // Fallback: cargar todos los diarios de efectivo y banco
                console.log("Usando fallback - buscando journals directamente");
                const journals = await this.orm.searchRead("account.journal", [
                    ["type", "in", ["cash", "bank"]],
                    ["company_id", "=", this.pos.company.id]
                ], ["id", "name", "type"]);
                
                console.log("Journals del fallback:", journals);
                
                // En el fallback, usar directamente el journal_id como id
                const formattedJournals = journals.map(j => ({
                    id: j.id,
                    journal_id: j.id,
                    name: j.name,
                    payment_method_id: null
                }));
                
                this.state.paymentMethods = formattedJournals;
                
                if (formattedJournals.length > 0) {
                    this.state.selectedPaymentMethod = formattedJournals[0].journal_id;
                    console.log("Método seleccionado por defecto:", formattedJournals[0]);
                }
            }
        } catch (error) {
            console.error("Error loading payment methods:", error);
        }
    }

    async searchPartners() {
        if (!this.state.partnerSearch.trim() || this.state.partnerSearch.trim().length < 2) {
            this.state.partners = [];
            this.state.showPartnerList = false;
            return;
        }
        
        this.state.loading = true;
        this.state.error = "";
        try {
            const partners = await this.orm.searchRead("res.partner", [
                "|", "|",
                ["name", "ilike", this.state.partnerSearch.trim()],
                ["vat", "ilike", this.state.partnerSearch.trim()],
                ["phone", "ilike", this.state.partnerSearch.trim()]
            ], ["id", "name", "vat", "phone"], { limit: 10 });
            this.state.partners = partners;
            this.state.showPartnerList = partners.length > 0;
        } finally {
            this.state.loading = false;
        }
    }

    async selectPartner(partner) {
        // Validar que no sea Consumidor Final (id=91158)
        if (partner.id === 91158) {
            this.dialog.add(ConfirmationDialog, { 
                title: _t("Cliente no válido"), 
                body: _t("No se pueden abonar apartados para el cliente 'Consumidor Final'. Por favor, seleccione otro cliente."),
                confirmText: _t("OK"),
                cancelText: false,
            });
            // Limpiar la búsqueda
            this.state.partnerSearch = "";
            this.state.showPartnerList = false;
            return;
        }
        
        this.state.selectedPartner = partner;
        this.state.partnerSearch = partner.name;
        this.state.showPartnerList = false;
        this.state.reservations = [];
        this.state.selectedReservationId = null;
        this.state.resv = null;
        this.state.error = "";
        
        // Buscar apartados del cliente
        await this.loadPartnerReservations();
    }

    async loadPartnerReservations() {
        if (!this.state.selectedPartner) return;
        
        this.state.loading = true;
        this.state.error = "";
        try {
            const reservations = await this.orm.searchRead("pos.reservation", [
                ["partner_id", "=", this.state.selectedPartner.id],
                ["state", "in", ["draft", "confirmed", "reserved", "paid"]]
            ], [
                "id", "name", "partner_id", "expiration_date", "amount_total", "amount_paid", "amount_due", "state"
            ]);
            
            this.state.reservations = reservations;
            
            if (reservations.length === 0) {
                this.state.error = _t("El cliente no tiene apartados activos");
            }
        } finally {
            this.state.loading = false;
        }
    }

    onAmountChange(ev) {
        const amount = parseFloat(ev.target.value) || 0;
        this.state.amount = amount;
        
        if (this.state.resv && amount > 0) {
            const amountDue = this.state.resv.amount_due || 0;
            if (amount > amountDue) {
                this.state.changeAmount = amount - amountDue;
                this.state.showChange = true;
            } else {
                this.state.changeAmount = 0;
                this.state.showChange = false;
            }
        } else {
            this.state.changeAmount = 0;
            this.state.showChange = false;
        }
    }

    onReservationChange(ev) {
        const resvId = parseInt(ev.target.value);
        if (resvId) {
            this.state.selectedReservationId = resvId;
            this.state.resv = this.state.reservations.find(r => r.id === resvId);
            this.state.error = "";
            // Reset change calculation when reservation changes
            this.state.changeAmount = 0;
            this.state.showChange = false;
            this.state.amount = 0;
        } else {
            this.state.selectedReservationId = null;
            this.state.resv = null;
            this.state.changeAmount = 0;
            this.state.showChange = false;
            this.state.amount = 0;
        }
    }

    clearPartnerSearch() {
        this.state.selectedPartner = null;
        this.state.partnerSearch = "";
        this.state.partners = [];
        this.state.showPartnerList = false;
        this.state.reservations = [];
        this.state.selectedReservationId = null;
        this.state.resv = null;
        this.state.error = "";
    }

    cancel() {
        this.props.close();
    }

    async confirm() {
        if (!this.state.selectedPartner) {
            this.state.error = _t("Seleccione un cliente");
            return;
        }
        if (!this.state.resv) {
            this.state.error = _t("Seleccione un apartado");
            return;
        }
        if (!(this.state.amount > 0)) {
            this.state.error = _t("Ingrese un monto válido");
            return;
        }
        if (!this.state.selectedPaymentMethod) {
            this.state.error = _t("Seleccione un método de pago");
            return;
        }

        // Si hay cambio, confirmar que el usuario está de acuerdo
        if (this.state.showChange && this.state.changeAmount > 0) {
            const confirmed = await this.confirmChangeAmount();
            if (!confirmed) {
                return;
            }
        }

        this.state.loading = true;
        this.state.error = "";
        try {
            // Calcular el monto exacto a aplicar (no más del saldo pendiente)
            const amountToApply = this.state.showChange ? 
                this.state.resv.amount_due : 
                this.state.amount;

            const result = await this.orm.call("pos.reservation", "add_payment", [
                this.state.resv.id, 
                { 
                    amount: amountToApply, 
                    journal_id: this.state.selectedPaymentMethod 
                }
            ]);
            
            // Print receipt
            const headerData = this.pos.getReceiptHeaderData(this.pos.get_order());
            const receiptData = {
                headerData,
                type: 'payment',
                name: this.state.resv.name,
                partner: (this.state.resv.partner_id && this.state.resv.partner_id[1]) || '',
                date: (new Date()).toLocaleString(),
                expiration_date: this.state.resv.expiration_date,
                ticket_number: result.ticket_number,
                amount: amountToApply,
                amount_received: this.state.amount, // Monto recibido del cliente
                change_amount: this.state.showChange ? this.state.changeAmount : 0,
                amount_total: this.state.resv.amount_total,
                amount_paid: result.amount_paid ?? (this.state.resv.amount_paid + amountToApply),
                amount_due: result.amount_due,
            };
            await this.printer.print(ReservationReceipt, { data: receiptData, formatCurrency: this.env.utils.formatCurrency }, { webPrintFallback: true });
            
            // Verificar si el apartado quedó completamente pagado después del abono
            if (result.state === 'paid' && result.amount_due <= 0) {
                // Preguntar si desea facturar inmediatamente
                const shouldInvoice = await this.askToInvoice();
                if (shouldInvoice) {
                    // Crear la factura inmediatamente
                    await this.createInvoiceAfterPayment(this.state.resv.id);
                }
            }
            
            this.props.close();
        } catch (error) {
            this.state.error = (error && error.message) || _t("No se pudo registrar el abono");
        } finally {
            this.state.loading = false;
        }
    }

    async confirmChangeAmount() {
        return new Promise((resolve) => {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Cambio a Devolver"),
                body: _t(`El monto ingresado ($${this.state.amount.toFixed(2)}) es mayor al saldo pendiente ($${this.state.resv.amount_due.toFixed(2)}). Se devolverá un cambio de $${this.state.changeAmount.toFixed(2)}. ¿Desea continuar?`),
                confirm: () => resolve(true),
                cancel: () => resolve(false),
                confirmLabel: _t("Sí, Continuar"),
                cancelLabel: _t("Cancelar"),
            });
        });
    }

    async askToInvoice() {
        return new Promise((resolve) => {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Apartado Pagado Completamente"),
                body: _t("El apartado ha sido pagado en su totalidad. ¿Desea crear la factura ahora?"),
                confirm: () => resolve(true),
                cancel: () => resolve(false),
                confirmLabel: _t("Sí, Facturar"),
                cancelLabel: _t("No, Después"),
            });
        });
    }

    async createInvoiceAfterPayment(reservationId) {
        this.state.loading = true;
        try {
            const result = await this.orm.call("pos.reservation", "create_invoice_from_pos_with_validation", [reservationId]);
            
            if (result.success) {
                // Mostrar notificación
                if (result.cufe) {
                    this.notification.add(
                        _t(`Factura creada y enviada a la DIAN exitosamente: ${result.invoice_name}. CUFE: ${result.cufe}`),
                        {
                            type: "success",
                            title: _t("Factura Validada"),
                        }
                    );
                } else {
                    this.notification.add(
                        _t(`Factura creada exitosamente: ${result.invoice_name}. Los pagos han sido conciliados.`),
                        {
                            type: "success",
                            title: _t("Factura Creada"),
                        }
                    );
                }
                
                // Imprimir el recibo de factura con CUFE y QR
                await this.printInvoiceReceipt(result);
            } else {
                this.notification.add(
                    result.message || _t("No se pudo crear la factura automáticamente"),
                    {
                        type: "warning",
                    }
                );
            }
        } catch (error) {
            this.notification.add(
                _t("Error al crear la factura: ") + (error?.message || ""),
                {
                    type: "danger",
                }
            );
        } finally {
            this.state.loading = false;
        }
    }

    async createInvoice() {
        if (!this.state.resv) {
            this.state.error = _t("Seleccione un apartado");
            return;
        }
        
        if (this.state.resv.state !== 'paid') {
            this.state.error = _t("El apartado debe estar completamente pagado para facturar");
            return;
        }

        this.state.loading = true;
        this.state.error = "";
        try {
            // Crear la factura siguiendo el flujo del POS
            const result = await this.orm.call("pos.reservation", "create_invoice_from_pos_with_validation", [this.state.resv.id]);
            
            if (result.success) {
                // Si hay CUFE/CUDE, la factura fue enviada a la DIAN exitosamente
                if (result.cufe) {
                    this.notification.add(
                        _t(`Factura creada y enviada a la DIAN exitosamente: ${result.invoice_name}. CUFE: ${result.cufe}`),
                        {
                            type: "success",
                            title: _t("Factura Validada"),
                        }
                    );
                } else {
                    this.notification.add(
                        _t(`Factura creada exitosamente: ${result.invoice_name}. Los pagos han sido conciliados.`),
                        {
                            type: "success",
                            title: _t("Factura Creada"),
                        }
                    );
                }
                
                // Imprimir el recibo de factura con CUFE y QR
                await this.printInvoiceReceipt(result);
                
                // Cerrar el popup después de crear la factura
                this.props.close();
            } else {
                this.state.error = result.message || _t("No se pudo crear la factura");
            }
        } catch (error) {
            this.state.error = (error && error.message) || _t("Error al crear la factura");
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Imprime el recibo de factura con CUFE y QR siguiendo el flujo de sh_pos_all_in_one_retail
     */
    async printInvoiceReceipt(invoiceResult) {
        if (!invoiceResult || !invoiceResult.invoice_data) {
            console.warn("No invoice data available for printing");
            return;
        }

        try {
            // Preparar datos para el recibo similar a cómo lo hace el POS
            const headerData = this.pos.getReceiptHeaderData ? 
                this.pos.getReceiptHeaderData(this.pos.get_order ? this.pos.get_order() : null) : 
                {
                    company: {
                        name: this.pos.company.name,
                        vat: this.pos.company.vat,
                        street: this.pos.company.street,
                        city: this.pos.company.city,
                        phone: this.pos.company.phone,
                        email: this.pos.company.email,
                        l10n_co_regime: this.pos.company.l10n_co_regime || '',
                        l10n_co_responsibility_ids: this.pos.company.l10n_co_responsibility_ids || [],
                    }
                };

            const receiptData = {
                headerData: headerData,
                type: 'invoice',
                reservation_name: this.state.resv.name,
                invoice_data: invoiceResult.invoice_data,
                payment_info: {
                    total_paid: this.state.resv.amount_paid || invoiceResult.invoice_data.amount_total,
                    previous_balance: 0,
                },
            };

            // Usar el servicio de impresión del POS
            // Esto es compatible con sh_pos_all_in_one_retail y sus configuraciones de impresión
            await this.printer.print(
                LayawayInvoiceReceipt, 
                { 
                    data: receiptData, 
                    formatCurrency: this.env.utils.formatCurrency 
                }, 
                { 
                    webPrintFallback: true 
                }
            );

            console.log("Invoice receipt printed successfully");
        } catch (error) {
            console.error("Error printing invoice receipt:", error);
            this.notification.add(
                _t("Factura creada pero hubo un error al imprimir el recibo"),
                {
                    type: "warning",
                }
            );
        }
    }
}

