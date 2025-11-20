/**
 * Prevent closing the Register Payment wizard without paying.
 * - Keeps modal (target='new') behavior, but disables: close (X), ESC key, backdrop click.
 * - Applies only to the register.payment.wizard by detecting the 'received_amount' field in the dialog.
 */

odoo.define('@odoo_parking_management/js/payment_wizard_guard', [], function (require) {
    'use strict';

    const { registry } = require('@web/core/registry');
    const { patch } = require('@web/core/utils/patch');
    const { Dialog } = require('@web/core/dialog/dialog');
    const { ActionDialog } = require('@web/webclient/actions/action_dialog');
    const { onWillUnmount } = require('@odoo/owl');

    function isOurPaymentWizard(modal) {
        // Strong marker from our view
        if (modal.querySelector('form.odpm-guard-form')) return true;
        // Fallback to presence of key field
        if (modal.querySelector('[name="received_amount"], input[name="received_amount"], div[name="received_amount"], .o_field_widget[name="received_amount"]')) return true;
        return false;
    }

    function hideCloseButtons(modal) {
        const candidates = modal.querySelectorAll(
            '.modal-header .btn-close, .modal-header [data-bs-dismiss="modal"], .modal-header .o_close, .modal-header .o_dialog_close, .modal-header .o_modal_close, .modal-header button[aria-label="Close"]'
        );
        for (const btn of candidates) {
            btn.style.display = 'none';
            btn.setAttribute('aria-hidden', 'true');
            btn.setAttribute('disabled', 'disabled');
            btn.setAttribute('data-disabled', 'true');
            btn.addEventListener('click', (ev) => {
                ev.preventDefault();
                ev.stopImmediatePropagation();
                return false;
            }, { capture: true });
        }
    }

    // A simple service that installs a MutationObserver once to guard the modal
    // Central gate: only allow dismiss/ESC for our wizard if authorized
    function shouldBlockDialog(self) {
        if (!isPaymentDialogInstance(self)) return false;
        return !window.__odpm_allow_close;
    }

    function isPaymentDialogInstance(self) {
        const el = self?.modalRef?.el;
        return !!(el && isOurPaymentWizard(el));
    }

    // Patch core Dialog to swallow ESC and header dismiss for our wizard
    patch(Dialog.prototype, {
        onEscape() {
            if (shouldBlockDialog(this)) {
                return; // ignore ESC
            }
            return super.onEscape();
        },
        async dismiss() {
            if (shouldBlockDialog(this)) {
                return; // ignore close button
            }
            return super.dismiss();
        },
    });

    // Patch ActionDialog to tweak modal and close button when it mounts
    patch(ActionDialog.prototype, {
        setup() {
            super.setup();
            const afterMount = () => {
                const modal = this.modalRef?.el;
                if (!modal || !isPaymentDialogInstance(this)) return;
                // Bootstrap attributes: block backdrop/keyboard
                modal.setAttribute('data-bs-backdrop', 'static');
                modal.setAttribute('data-bs-keyboard', 'false');
                modal.classList.add('odpm-guard');
                // Fix accessibility warnings: remove 'for' on labels when target id is missing (readonly fields rendered as spans)
                const labels = modal.querySelectorAll('.modal-body .o_form_label[for]');
                labels.forEach((lbl) => {
                    const id = lbl.getAttribute('for');
                    if (id && !modal.querySelector(`#${CSS.escape(id)}`)) {
                        lbl.removeAttribute('for');
                    }
                });
                // Hide entire header (removes X and debug)
                const header = modal.querySelector('.modal-header');
                if (header) {
                    header.style.display = 'none';
                }
                // Allow close after Pay button click
                const payBtn = modal.querySelector('button[name="parking_payment"]');
                if (payBtn) {
                    payBtn.addEventListener('click', () => {
                        window.__odpm_allow_close = true;
                        setTimeout(() => { window.__odpm_allow_close = false; }, 10000);
                    }, { once: true });
                }
                // After the dialog actually closes, reload the underlying action to reflect new state
                modal.addEventListener('hidden.bs.modal', () => {
                    try {
                        this.env.services.action?.reload();
                    } catch (e) {
                        // ignore
                    }
                }, { once: true });
            };
            // execute after mount
            setTimeout(afterMount);
            // Observe changes in modal to re-apply guards
            const obs = new MutationObserver(() => setTimeout(afterMount));
            const modalEl = this.modalRef?.el;
            if (modalEl) {
                obs.observe(modalEl, { childList: true, subtree: true });
            }
            onWillUnmount(() => obs.disconnect());
        },
    });

    // Global hard guard (capture phase): block ESC, header close and backdrop click when our wizard is open
    function globalGuardsStart() {
        const escGuard = (ev) => {
            if (ev.key !== 'Escape') return;
            const hasGuard = document.querySelector('.modal:has(.odpm-guard-form), .odpm-guard-form');
            if (hasGuard && !window.__odpm_allow_close) {
                ev.stopImmediatePropagation();
                ev.preventDefault();
            }
        };
        const clickGuard = (ev) => {
            const modal = ev.target.closest('.modal');
            if (!modal) return;
            const isGuard = !!modal.querySelector('.odpm-guard-form');
            if (!isGuard || window.__odpm_allow_close) return;
            // Backdrop click
            if (ev.target === modal) {
                ev.stopImmediatePropagation();
                ev.preventDefault();
                return;
            }
            // Header close or any dismiss button
            if (ev.target.closest('.modal-header') || ev.target.closest('[data-bs-dismiss="modal"], .btn-close, [aria-label="Close"]')) {
                ev.stopImmediatePropagation();
                ev.preventDefault();
            }
        };
        // Capture on window and document for maximum priority
        window.addEventListener('keydown', escGuard, true);
        document.addEventListener('keydown', escGuard, true);
        document.addEventListener('click', clickGuard, true);
    }

    registry.category('services').add('odpm_payment_wizard_guard', { start: globalGuardsStart });
});
