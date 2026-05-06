/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

const megaFormService = {
    dependencies: ["notification"],
    start(env, { notification }) {

        const initForm = async () => {
            const form = document.getElementById("leadFormMega");
            const brandSelect = document.getElementById("brand_id");
            const brandNameInput = document.getElementById("brand_name");
            const modelSelect = document.getElementById("model_id");
            const modelNameInput = document.getElementById("model_name");
            const messageBox = document.getElementById("leadDemoMessage");
            const submitBtn = document.getElementById("leadDemoSubmitBtn");

            if (!form) {
                console.warn("⚠️ Formulario 'leadFormMega' no encontrado");
                return;
            }

            console.log("✅ Formulario listo:", form);

            // ✅ Función showMessage DENTRO de initForm
            function showMessage(type, message) {
                if (!messageBox) return;
                messageBox.className = `alert alert-${type} mt-3`;
                messageBox.textContent = message;
                messageBox.classList.remove("d-none");
            }

            // ✅ Función clearMessage DENTRO de initForm
            function clearMessage() {
                if (!messageBox) return;
                messageBox.className = "alert d-none mt-3";
                messageBox.textContent = "";
            }

            // Cargar marcas al iniciar
            await loadBrands();

            // Evento submit
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

                    console.log("✅ Lead enviado:", result);
                    showMessage("success", "✅ ¡Quedamos atentos! Tu solicitud fue enviada con éxito. En los próximos minutos te contactaremos por WhatsApp. ¡Gracias por confiar en Megatecnicentro!");
                    form.reset();
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Solicitar servicio";

                } catch (error) {
                    console.error("❌ Error:", error);
                    showMessage("danger", "No fue posible enviar la información.");
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Solicitar servicio";
                }
            });

            // Evento change en marcas
            brandSelect.addEventListener("change", async () => {
                const selectedOption = brandSelect.options[brandSelect.selectedIndex];
                brandNameInput.value = selectedOption && brandSelect.value ? selectedOption.text : "";
                resetModelSelect();

                if (brandSelect.value) {
                    await loadModels(brandSelect.value);
                }
            });

            // Funciones auxiliares
            function resetModelSelect() {
                modelSelect.innerHTML = '<option value="">Seleccione un modelo...</option>';
                modelNameInput.value = "";
            }

            async function loadBrands() {
                if (!brandSelect) return;
                try {
                    const brands = await rpc("/lead/brands", {});
                    brandSelect.innerHTML = '<option value="">Seleccione una marca...</option>';
                    brands.forEach(brand => {
                        brandSelect.add(new Option(brand.name, brand.id));
                    });
                    console.log("✅ Marcas cargadas:", brands.length);
                } catch (error) {
                    console.error("❌ Error cargando marcas:", error);
                }
            }

            async function loadModels(brandId) {
                try {
                    const models = await rpc("/lead/models", { brand_id: brandId });
                    modelSelect.innerHTML = '<option value="">Seleccione un modelo...</option>';
                    models.forEach(model => {
                        modelSelect.add(new Option(model.name, model.id));
                    });
                } catch (error) {
                    console.error("❌ Error cargando modelos:", error);
                }
            }
        };

        // Iniciar
        if (document.readyState === "complete") {
            initForm();
        } else {
            window.addEventListener("load", initForm);
        }
    },
};

registry.category("services").add("megaFormService", megaFormService);
