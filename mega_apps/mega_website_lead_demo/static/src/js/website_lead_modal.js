/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

let leadModalInitialized = false;

async function initLeadModal() {
    if (leadModalInitialized) {
        return;
    }

    const modalEl = document.getElementById("leadDemoModal");
    const form = document.getElementById("leadDemoForm");

    if (!modalEl || !form) {
        console.warn("No se encontró leadDemoModal o leadDemoForm en el DOM");
        return;
    }

    const messageBox = document.getElementById("leadDemoMessage");
    const submitBtn = document.getElementById("leadDemoSubmitBtn");
    const openBtn = document.querySelector('[data-bs-target="#leadDemoModal"]');

    leadModalInitialized = true;

    function showMessage(type, message) {
        const t = messageBox.classList
        if (!messageBox) return;
        messageBox.className = `alert alert-${type} mt-3`;
        messageBox.textContent = message;
        messageBox.style.display = "block";
    }

    function clearMessage() {
        if (!messageBox) return;
        messageBox.className = "alert mt-3";
        messageBox.style.display = "none";
    }

    function resetFormState() {
        form.reset();
        submitBtn.disabled = false;
    }

    // Limpiar mensaje al abrir el modal
    modalEl.addEventListener("show.bs.modal", () => {
        clearMessage();
    });

    // Quitar foco al cerrar
    modalEl.addEventListener("hide.bs.modal", () => {
        if (document.activeElement && modalEl.contains(document.activeElement)) {
            document.activeElement.blur();
        }
    });

    // Devolver foco al botón
    modalEl.addEventListener("hidden.bs.modal", () => {
        if (openBtn) {
            openBtn.focus();
        }
    });

    // Enviar formulario
    form.addEventListener("submit", async (ev) => {
        ev.preventDefault();

        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        // clearMessage();
        submitBtn.disabled = true;
        // submitBtn.textContent = "Enviando...";

        try {
            const formData = new FormData(form);
            const params = Object.fromEntries(formData.entries());
            const result = await rpc("/lead/submit", params);
            if (!result.success) {
                showMessage("danger", result.message || "❌ No pudimos procesar tu solicitud. Intenta nuevamente.");
                submitBtn.disabled = false;
                submitBtn.textContent = "Solicitar servicio";
                return;
            }
            // ✅ Éxito - Mostrar mensaje UNA SOLA VEZ
            showMessage(
                "success",
                result.message || "¡Solicitud enviada! Pronto te contactaremos por WhatsApp."
            );
            // ✅ Abrir WhatsApp si hay URL
            if (result.whatsapp_url) {
                window.open(
                    result.whatsapp_url,
                    "_blank",
                    "noopener,noreferrer"
                );
            }

            // ✅ Resetear formulario
            resetFormState();

        } catch (error) {
            console.error("❌ Error enviando lead:", error);
            showMessage("danger", "❌ No fue posible enviar la información. Intente nuevamente.");
            submitBtn.disabled = false;
            submitBtn.textContent = "Solicitar servicio";
        }
    });
}

// Iniciar cuando el DOM esté listo
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initLeadModal);
} else {
    initLeadModal();
}
