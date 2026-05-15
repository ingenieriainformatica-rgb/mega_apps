/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

let leadModalInitialized = false;
let whatsappDirectInitialized = false;

function storeUtmParams() {
    const params = new URLSearchParams(window.location.search);

    ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"].forEach((key) => {
        const value = params.get(key);
        if (value) {
            sessionStorage.setItem(key, value);
        }
    });
}

async function initLeadModal() {
    if (leadModalInitialized) {
        return;
    }

    const modalEl = document.getElementById("leadDemoModal");
    const form = document.getElementById("leadDemoForm");

    // Si ya no existe el modal, no pasa nada. El flujo nuevo puede funcionar igual.
    if (!modalEl || !form) {
        return;
    }

    const messageBox = document.getElementById("leadDemoMessage");
    const submitBtn = document.getElementById("leadDemoSubmitBtn");
    const openBtn = document.querySelector('[data-bs-target="#leadDemoModal"]');

    if (!submitBtn) {
        console.warn("No se encontró leadDemoSubmitBtn en el DOM");
        return;
    }

    leadModalInitialized = true;

    function showMessage(type, message) {
        if (!messageBox) {
            return;
        }

        messageBox.className = `alert alert-${type} mt-3`;
        messageBox.textContent = message;
        messageBox.style.display = "block";
    }

    function clearMessage() {
        if (!messageBox) {
            return;
        }

        messageBox.className = "alert mt-3 d-none";
        messageBox.textContent = "";
        messageBox.style.display = "none";
    }

    function resetFormState() {
        form.reset();
        submitBtn.disabled = false;
    }

    modalEl.addEventListener("show.bs.modal", () => {
        clearMessage();
    });

    modalEl.addEventListener("hide.bs.modal", () => {
        if (document.activeElement && modalEl.contains(document.activeElement)) {
            document.activeElement.blur();
        }
    });

    modalEl.addEventListener("hidden.bs.modal", () => {
        if (openBtn) {
            openBtn.focus();
        }
    });

    form.addEventListener("submit", async (ev) => {
        ev.preventDefault();

        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        submitBtn.disabled = true;

        try {
            const formData = new FormData(form);
            const params = Object.fromEntries(formData.entries());

            const result = await rpc("/lead/submit", params);

            if (!result.success) {
                showMessage(
                    "danger",
                    result.message || "❌ No pudimos procesar tu solicitud. Intenta nuevamente."
                );
                submitBtn.disabled = false;
                return;
            }

            showMessage(
                "success",
                result.message || "¡Solicitud enviada! Pronto te contactaremos por WhatsApp."
            );

            if (result.whatsapp_url) {
                window.open(result.whatsapp_url, "_blank", "noopener,noreferrer");
            }

            resetFormState();

        } catch (error) {
            console.error("❌ Error enviando lead:", error);
            showMessage("danger", "❌ No fue posible enviar la información. Intente nuevamente.");
            submitBtn.disabled = false;
        }
    });
}

function initWhatsappDirectButtons() {
    if (whatsappDirectInitialized) {
        return;
    }

    const buttons = document.querySelectorAll(".js-whatsapp-lead-click");

    if (!buttons.length) {
        return;
    }

    whatsappDirectInitialized = true;

    buttons.forEach((button) => {
        button.addEventListener("click", async (ev) => {
            ev.preventDefault();

            /*
             * Evita doble clic mientras se crea el lead.
             * Importante: NO deshabilitamos el botón visualmente.
             */
            if (button.dataset.loading === "1") {
                return;
            }

            button.dataset.loading = "1";

            try {
                const payload = buildWhatsappTrackingPayload(button);

                const result = await rpc("/lead/whatsapp/track", payload);

                if (result && result.whatsapp_url) {
                    delete button.dataset.loading;

                    button.href = result.whatsapp_url;
                    button.target = "_blank";

                    window.open(result.whatsapp_url, "_blank");

                    return;
                }

                delete button.dataset.loading;

            } catch (error) {
                // console.error("❌ Error registrando clic de WhatsApp:", error);

                /*
                 * Siempre liberar el botón si hubo error.
                 */
                delete button.dataset.loading;

                // redirectToWhatsappFallback(button);
            }
        });
    });
}

function buildWhatsappTrackingPayload(button) {
    const currentUrl = new URL(window.location.href);
    const params = currentUrl.searchParams;

    return {
        page_url: window.location.href,
        page_path: window.location.pathname,
        page_title: document.title,
        referrer: document.referrer || "",

        lead_source: button.dataset.leadSource || "whatsapp_direct",
        lead_button: button.dataset.leadButton || "unknown_button",

        utm_source: params.get("utm_source") || sessionStorage.getItem("utm_source") || "",
        utm_medium: params.get("utm_medium") || sessionStorage.getItem("utm_medium") || "",
        utm_campaign: params.get("utm_campaign") || sessionStorage.getItem("utm_campaign") || "",
        utm_content: params.get("utm_content") || sessionStorage.getItem("utm_content") || "",
        utm_term: params.get("utm_term") || sessionStorage.getItem("utm_term") || "",
    };
}

function redirectToWhatsappFallback(button) {
    const fallbackUrl = button.getAttribute("href") || button.dataset.fallbackUrl || "/lead/whatsapp/start";

    const link = document.createElement("a");
    link.href = fallbackUrl;
    link.target = "_blank";
    link.click();
}

function initLeadWebsiteTools() {
    storeUtmParams();
    initLeadModal();
    initWhatsappDirectButtons();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initLeadWebsiteTools);
} else {
    initLeadWebsiteTools();
}
