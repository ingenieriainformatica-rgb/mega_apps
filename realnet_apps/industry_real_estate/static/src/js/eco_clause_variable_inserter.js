/** @odoo-module **/

import { registry } from "@web/core/registry";

// ---- Config/Helpers --------------------------------------------------------

const CLAUSE_VARS = [
    "ARRENDATARIO_DOCUMENTO",
    "ARRENDATARIO_ENCABEZADO",
    "ARRENDATARIO_NOMBRE",
    "COMISION_MENSUAL",
    "CONTRATO_CANON",
    "CONTRATO_CANON_LETRAS",
    "CONTRATO_DURACION",
    "DEUDORES_SOLIDARIOS",
    "DOCUMENTO_DEUDOR_SOLIDARIO",
    "FECHA_FIN_CONTRATO_LETRAS",
    "FECHA_INICIO_CONTRATO_LETRAS",
    "FORMAS_PAGO_LISTA_COMPLETA",
    "INMUEBLE_DIRECCION",
    "INMUEBLE_MUNICIPIO",
    "INMUEBLE_NUMERO_CUARTO_UTIL",
    "INMUEBLE_NUMERO_PARQUEADERO",
    "LINEA_TELEFONICA",
    "MUNICIPIO",
    "NOMBRE_ARRENDADOR",
    "NOMBRE_DEUDOR_SOLIDARIO",
    "PROPIETARIOS_LISTA_COMPLETA",
    "PROYECTO_NOMBRE",
    "SOLICITUD_DESTINO_INMUEBLE",
    "RAZON_SOCIAL_ARRENDADOR"
];

function makeToken(varName) {
    return "${" + varName + "}";
}

function renderChipsHTML(vars) {
    return `
      <div class="o_contract_vars_palette_content" style="min-height:82px; padding:6px 0;">
        ${vars
            .map(
                (v) =>
                    `<span class="oe-clause-var o_badge o_badge_primary"
                           draggable="true"
                           data-var="${v}"
                           style="margin:4px; padding:4px 8px; display:inline-block; cursor:pointer;">${v}</span>`
            )
            .join("")}
      </div>`;
}

// Inserción en textarea
function insertInTextarea(el, token) {
    const start = el.selectionStart ?? el.value.length;
    const end = el.selectionEnd ?? el.value.length;
    el.value = el.value.slice(0, start) + token + el.value.slice(end);
    const pos = start + token.length;
    el.selectionStart = el.selectionEnd = pos;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
}

// Inserción en contenteditable
function insertInEditable(el, token) {
    el.focus();
    const ok = document.execCommand && document.execCommand("insertText", false, token);
    if (!ok) {
        const sel = window.getSelection();
        if (!sel || !sel.rangeCount) return;
        const range = sel.getRangeAt(0);
        range.deleteContents();
        range.insertNode(document.createTextNode(token));
        range.collapse(false);
        sel.removeAllRanges();
        sel.addRange(range);
    }
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
}

// Encuentra el editor activo dentro de un contenedor .o_contract_vars
function findActiveTarget() {
    const active = document.activeElement;
    const container = active && active.closest(".o_contract_vars");
    if (!container) return { textarea: null, editable: null };

    const editable =
        container.querySelector('[contenteditable="true"]') ||
        container.querySelector('.note-editable[contenteditable="true"]');
    const textarea = container.querySelector("textarea");

    return { textarea, editable };
}

// Pinta la paleta en cada contenedor vacío
function hydratePalettes(root = document) {
    const hosts = root.querySelectorAll(".o_contract_vars_palette");
    for (const host of hosts) {
        if (!host.dataset.hydrated) {
            host.innerHTML = renderChipsHTML(CLAUSE_VARS);
            host.dataset.hydrated = "1";
        }
    }
}

// ---- Service ---------------------------------------------------------------

const Service = {
    start(env) {
        const notify = (title, message, type = "warning") =>
            env.services.notification.add(message, { title, type });

        // 1) Hidrata paletas al cargar y cuando se abren formularios (diálogos)
        hydratePalettes(document);

        // Observa cambios en DOM para hidratar paletas insertadas después (diálogos, pestañas, etc.)
        const mo = new MutationObserver((mutations) => {
            for (const m of mutations) {
                for (const node of m.addedNodes || []) {
                    if (!(node instanceof HTMLElement)) continue;
                    if (node.matches?.(".o_form_view, .modal, .o_dialog_container, .o_content")) {
                        hydratePalettes(node);
                    } else {
                        // hidrata si en el subárbol aparecen contenedores
                        const any = node.querySelector?.(".o_contract_vars_palette");
                        if (any) hydratePalettes(node);
                    }
                }
            }
        });
        mo.observe(document.body, { childList: true, subtree: true });

        // 2) Click en chip → inserta
        document.addEventListener("click", (ev) => {
            const chip = ev.target.closest(".oe-clause-var");
            if (!chip) return;
            const varName = chip.dataset.var;
            if (!varName) return;

            const token = makeToken(varName);
            const { textarea, editable } = findActiveTarget();

            if (editable) return insertInEditable(editable, token);
            if (textarea) return insertInTextarea(textarea, token);

            notify(
                "Inserción de variables",
                "Selecciona y arrastra la variable al campo en el que desees implementar."
            );
        });

        // 3) Drag & drop
        document.addEventListener("dragstart", (ev) => {
            const chip = ev.target.closest(".oe-clause-var");
            if (!chip) return;
            const v = chip.dataset.var;
            if (v) ev.dataTransfer?.setData("text/plain", makeToken(v));
        });
        document.addEventListener("dragover", (ev) => {
            if (ev.target.closest(".o_contract_vars [contenteditable='true'], .o_contract_vars textarea")) {
                ev.preventDefault();
            }
        });
        document.addEventListener("drop", (ev) => {
            const token = ev.dataTransfer?.getData("text/plain");
            if (!token) return;
            const container = ev.target.closest(".o_contract_vars");
            if (!container) return;

            const editable = container.querySelector("[contenteditable='true']");
            const textarea = container.querySelector("textarea");

            if (editable) { ev.preventDefault(); insertInEditable(editable, token); }
            else if (textarea) { ev.preventDefault(); insertInTextarea(textarea, token); }
        });
    },
};

registry.category("services").add("eco_clause_variable_service", Service);
