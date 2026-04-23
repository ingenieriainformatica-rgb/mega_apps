/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

let leadModalInitialized = false;

async function initLeadModal() {
    if (leadModalInitialized) {
        console.log("Lead modal ya estaba inicializado");
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
    const brandSelect = document.getElementById("brand_id");
    const modelSelect = document.getElementById("model_id");
    const brandNameInput = document.getElementById("brand_name");
    const modelNameInput = document.getElementById("model_name");
    const openBtn = document.querySelector('[data-bs-target="#leadDemoModal"]');

    if (!brandSelect || !modelSelect || !submitBtn || !brandNameInput || !modelNameInput) {
        console.warn("Faltan elementos del formulario");
        return;
    }

    leadModalInitialized = true;

    async function loadBrands() {
        try {
            const brands = await rpc("/lead/brands", {});
            brandSelect.innerHTML = '<option value="">Seleccione una marca...</option>';

            for (const brand of brands) {
                const option = document.createElement("option");
                option.value = brand.id;
                option.textContent = brand.name;
                brandSelect.appendChild(option);
            }
        } catch (error) {
            console.error("Error cargando marcas:", error);
        }
    }

    async function loadModels(brandId) {
        try {
            const models = await rpc("/lead/models", { brand_id: brandId });
            modelSelect.innerHTML = '<option value="">Seleccione un modelo...</option>';

            for (const model of models) {
                const option = document.createElement("option");
                option.value = model.id;
                option.textContent = model.name;
                modelSelect.appendChild(option);
            }
        } catch (error) {
            console.error("Error cargando modelos:", error);
        }
    }

    function showMessage(type, message) {
        if (!messageBox) {
            return;
        }
        messageBox.className = `alert alert-${type} mt-3`;
        messageBox.textContent = message;
        messageBox.classList.remove("d-none");
    }

    function clearMessage() {
        if (!messageBox) {
            return;
        }
        messageBox.className = "alert d-none mt-3";
        messageBox.textContent = "";
    }

    function resetModelSelect() {
        modelSelect.innerHTML = '<option value="">Seleccione un modelo...</option>';
        modelNameInput.value = "";
    }

    function resetFormState() {
        form.reset();
        brandNameInput.value = "";
        modelNameInput.value = "";
        resetModelSelect();
        clearMessage();
        submitBtn.disabled = false;
        submitBtn.textContent = "Solicitar servicio";
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

    brandSelect.addEventListener("change", async () => {
        const selectedOption = brandSelect.options[brandSelect.selectedIndex];
        brandNameInput.value = selectedOption && brandSelect.value ? selectedOption.text : "";

        resetModelSelect();

        if (brandSelect.value) {
            await loadModels(brandSelect.value);
        }
    });

    modelSelect.addEventListener("change", () => {
        const selectedOption = modelSelect.options[modelSelect.selectedIndex];
        modelNameInput.value = selectedOption && modelSelect.value ? selectedOption.text : "";
    });

    form.addEventListener("submit", async (ev) => {
        ev.preventDefault();

        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        clearMessage();
        submitBtn.disabled = true;
        submitBtn.textContent = "Enviando...";

        try {
            const formData = new FormData(form);
            const params = Object.fromEntries(formData.entries());

            const result = await rpc("/lead/submit", params);

            if (!result.success) {
                showMessage("danger", result.message || "Ocurrió un error.");
                submitBtn.disabled = false;
                submitBtn.textContent = "Solicitar servicio";
                return;
            }

            if (result.whatsapp_url) {
                window.open(result.whatsapp_url, "_blank", "noopener,noreferrer");
            }

            console.log("Lead enviado correctamente.", result);

            showMessage("success", "Información enviada correctamente.");

            resetFormState();

            submitBtn.disabled = false;
            submitBtn.textContent = "Solicitar servicio";

        } catch (error) {
            console.error("Error enviando lead:", error);
            showMessage("danger", "No fue posible enviar la información.");
            submitBtn.disabled = false;
            submitBtn.textContent = "Solicitar servicio";
        }
    });

    await loadBrands();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initLeadModal);
} else {
    initLeadModal();
}
